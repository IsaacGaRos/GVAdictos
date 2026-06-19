from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def port_accepts_connection(host: str, port: int, timeout: float = 2.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def run_text(command: list[str], timeout: float = 5.0) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return completed.stdout + completed.stderr


def listening_pids(port: int) -> list[int]:
    output = run_text(["netstat", "-ano", "-p", "tcp"])
    pids: set[int] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        state = parts[3].upper()
        pid_raw = parts[-1]
        if state != "LISTENING":
            continue
        if not local_address.endswith(f":{port}"):
            continue
        if pid_raw.isdigit():
            pids.add(int(pid_raw))
    return sorted(pids)


def process_info(pid: int) -> dict[str, str | int | bool]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
            "if ($p) { $p | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress }"
        ),
    ]
    output = run_text(command)
    try:
        data = json.loads(output) if output.strip() else {}
    except json.JSONDecodeError:
        data = {}
    command_line = str(data.get("CommandLine") or "")
    name = str(data.get("Name") or "")
    return {
        "pid": pid,
        "name": name,
        "command_line": command_line,
        "looks_like_streamlit": "streamlit" in command_line.lower() or "streamlit" in name.lower(),
    }


def http_check(url: str, timeout: float = 5.0) -> dict[str, object]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                "ok": 200 <= response.status < 500,
                "status": response.status,
                "reason": response.reason,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        return {"ok": True, "status": exc.code, "reason": exc.reason, "error": ""}
    except Exception as exc:
        return {"ok": False, "status": None, "reason": "", "error": str(exc)}


def latest_log_snippets(max_lines: int = 25) -> list[dict[str, object]]:
    if not LOGS_DIR.exists():
        return []
    candidates = sorted(LOGS_DIR.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    selected: list[Path] = []
    for path in candidates:
        name_hit = "streamlit" in path.name.lower()
        text_hit = False
        if not name_hit:
            try:
                text_hit = "streamlit" in path.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                text_hit = False
        if name_hit or text_hit:
            selected.append(path)
        if len(selected) >= 3:
            break

    snippets = []
    for path in selected:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
        except OSError as exc:
            lines = [f"Could not read log: {exc}"]
        snippets.append({"path": str(path), "lines": lines})
    return snippets


def recommendation(port_occupied: bool, processes: list[dict[str, object]], http: dict[str, object]) -> str:
    if not port_occupied:
        return "reiniciar_manual: el puerto no esta ocupado; lanzar Streamlit si se necesita QA visual."
    if http["ok"] and any(process["looks_like_streamlit"] for process in processes):
        return "continuar: Streamlit parece vivo y responde HTTP."
    if http["ok"]:
        return "continuar_con_cautela: el puerto responde HTTP, aunque el proceso no parece Streamlit."
    if any(process["looks_like_streamlit"] for process in processes):
        return "esperar_o_revisar_logs: Streamlit ocupa el puerto pero no responde HTTP; no reiniciar en bucle."
    return "revisar_conflicto: el puerto esta ocupado por otro proceso; reinicio manual solo tras confirmar."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Non-destructive Streamlit diagnostic.")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--url", default="")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    url = args.url or f"http://localhost:{args.port}"
    occupied = port_accepts_connection(args.host, args.port)
    pids = listening_pids(args.port) if occupied else []
    processes = [process_info(pid) for pid in pids]
    http = http_check(url) if occupied else {"ok": False, "status": None, "reason": "", "error": "port closed"}
    logs = latest_log_snippets()
    payload = {
        "checked_at": now_iso(),
        "port": args.port,
        "host": args.host,
        "port_occupied": occupied,
        "processes": processes,
        "looks_like_streamlit": any(process["looks_like_streamlit"] for process in processes),
        "probable_url": url,
        "http": http,
        "log_snippets": logs,
        "recommendation": recommendation(occupied, processes, http),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Streamlit diagnostic at {payload['checked_at']}")
        print(f"Port {args.port} occupied: {occupied}")
        if processes:
            for process in processes:
                print(
                    f"PID {process['pid']} {process['name']} "
                    f"streamlit={process['looks_like_streamlit']}"
                )
                print(f"  {process['command_line']}")
        else:
            print("PID/process: none detected")
        print(f"Probable URL: {url}")
        print(f"HTTP ok: {http['ok']} status={http['status']} error={http['error']}")
        if logs:
            print("Recent logs:")
            for snippet in logs:
                print(f"- {snippet['path']}")
                for line in snippet["lines"][-5:]:
                    print(f"  {line}")
        else:
            print("Recent logs: none found in logs/")
        print(f"Recommendation: {payload['recommendation']}")

    return 0 if http["ok"] or not occupied else 1


if __name__ == "__main__":
    raise SystemExit(main())
