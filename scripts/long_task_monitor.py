from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_slug(command: list[str]) -> str:
    raw = "_".join(Path(part).stem if part.endswith(".py") else part for part in command[:4])
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in raw).strip("_")
    return (cleaned or "command")[:80]


def command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def reader_thread(stream, stream_name: str, output_queue: queue.Queue[tuple[str, str]]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output_queue.put((stream_name, line.rstrip("\n")))
    finally:
        stream.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wrap a long-running command and write stdout/stderr plus liveness metadata to logs/."
    )
    parser.add_argument(
        "--silent-after",
        type=float,
        default=60.0,
        help="Seconds without output before status is considered silent.",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=30.0,
        help="Seconds between monitor status lines while the command is still running.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")
    return parser


def drain_available(
    output_queue: queue.Queue[tuple[str, str]],
    captured: list[dict[str, str]],
    echo: bool = True,
) -> tuple[bool, str | None]:
    saw_output = False
    last_line = None
    while True:
        try:
            stream_name, line = output_queue.get_nowait()
        except queue.Empty:
            break
        saw_output = True
        last_line = line
        entry = {"at": now_iso(), "stream": stream_name, "line": line}
        captured.append(entry)
        if echo:
            prefix = "STDERR" if stream_name == "stderr" else "STDOUT"
            print(f"[{entry['at']}] {prefix}: {line}", flush=True)
    return saw_output, last_line


def write_logs(
    *,
    command: list[str],
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    exit_code: int | None,
    captured: list[dict[str, str]],
    last_output_at: str | None,
    last_output_line: str | None,
    silent_after: float,
    silent_events: list[dict[str, object]],
) -> tuple[Path, Path]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    base = LOGS_DIR / f"long_task_{timestamp()}_{safe_slug(command)}"
    log_path = base.with_suffix(".log")
    json_path = base.with_suffix(".json")

    no_output_seconds = None
    if last_output_at:
        last_dt = datetime.fromisoformat(last_output_at)
        end_dt = datetime.fromisoformat(ended_at)
        no_output_seconds = round((end_dt - last_dt).total_seconds(), 2)

    status = "completed"
    if exit_code is None:
        status = "unknown"
    elif exit_code != 0:
        status = "failed"

    payload = {
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration_seconds, 2),
        "command": command,
        "command_text": command_text(command),
        "exit_code": exit_code,
        "status": status,
        "silent_after_seconds": silent_after,
        "last_output_at": last_output_at,
        "last_output_line": last_output_line,
        "seconds_since_last_output_at_exit": no_output_seconds,
        "appeared_silent_at_exit": bool(no_output_seconds is not None and no_output_seconds >= silent_after),
        "silent_events": silent_events,
        "output": captured,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Long task monitor",
        "",
        f"Started: {started_at}",
        f"Ended: {ended_at}",
        f"Duration seconds: {round(duration_seconds, 2)}",
        f"Command: {command_text(command)}",
        f"Exit code: {exit_code}",
        f"Last output at: {last_output_at or 'none'}",
        f"Last output line: {last_output_line or 'none'}",
        f"Appeared silent at exit: {payload['appeared_silent_at_exit']}",
        "",
        "## Output",
        "",
    ]
    for entry in captured:
        lines.append(f"[{entry['at']}] {entry['stream'].upper()}: {entry['line']}")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path, json_path


def main() -> int:
    args = build_parser().parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("ERROR: pass a command after --", file=sys.stderr)
        return 2

    started_at = now_iso()
    start_time = time.monotonic()
    output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
    captured: list[dict[str, str]] = []
    silent_events: list[dict[str, object]] = []
    last_output_at: str | None = None
    last_output_line: str | None = None
    last_output_monotonic = time.monotonic()
    last_heartbeat = 0.0

    print(f"[{started_at}] START {command_text(command)}", flush=True)
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        ended_at = now_iso()
        duration = time.monotonic() - start_time
        captured.append({"at": ended_at, "stream": "stderr", "line": f"Failed to start: {exc}"})
        log_path, json_path = write_logs(
            command=command,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration,
            exit_code=127,
            captured=captured,
            last_output_at=ended_at,
            last_output_line=f"Failed to start: {exc}",
            silent_after=args.silent_after,
            silent_events=silent_events,
        )
        print(f"ERROR: failed to start command: {exc}", file=sys.stderr)
        print(f"Wrote {log_path}")
        print(f"Wrote {json_path}")
        return 127

    threads = [
        threading.Thread(target=reader_thread, args=(process.stdout, "stdout", output_queue), daemon=True),
        threading.Thread(target=reader_thread, args=(process.stderr, "stderr", output_queue), daemon=True),
    ]
    for thread in threads:
        thread.start()

    try:
        while process.poll() is None:
            saw_output, line = drain_available(output_queue, captured)
            if saw_output:
                last_output_at = captured[-1]["at"]
                last_output_line = line
                last_output_monotonic = time.monotonic()

            now = time.monotonic()
            silent_for = now - last_output_monotonic
            if now - last_heartbeat >= args.heartbeat_interval:
                state = "silent" if silent_for >= args.silent_after else "alive"
                event = {
                    "at": now_iso(),
                    "state": state,
                    "pid": process.pid,
                    "silent_for_seconds": round(silent_for, 2),
                }
                silent_events.append(event)
                print(
                    f"[{event['at']}] MONITOR: pid={process.pid} state={state} "
                    f"silent_for={event['silent_for_seconds']}s",
                    flush=True,
                )
                last_heartbeat = now
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("KeyboardInterrupt: terminating wrapped command...", file=sys.stderr, flush=True)
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    for thread in threads:
        thread.join(timeout=2)
    drain_available(output_queue, captured)

    exit_code = process.returncode
    ended_at = now_iso()
    duration = time.monotonic() - start_time
    if captured and last_output_at is None:
        last_output_at = captured[-1]["at"]
        last_output_line = captured[-1]["line"]

    log_path, json_path = write_logs(
        command=command,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration,
        exit_code=exit_code,
        captured=captured,
        last_output_at=last_output_at,
        last_output_line=last_output_line,
        silent_after=args.silent_after,
        silent_events=silent_events,
    )

    print(f"[{ended_at}] END exit_code={exit_code} duration={round(duration, 2)}s")
    print(f"Wrote {log_path}")
    print(f"Wrote {json_path}")
    return int(exit_code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
