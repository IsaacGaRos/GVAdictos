# 🧠 Memory Compact Dump

**Last updated**: 2026-06-17T21:00:00 UTC  
**Project**: GVAdictos  
**Status**: GitHub integration + EUR-Lex import COMPLETE

---

## 👤 Work Context (Isaac)

- **Location**: Paterna/Tavernes Blanques, Valencia, ES (Europe/Madrid timezone)
- **Technical skills**: C#/.NET, DLL modules, GitHub, oposición prep, Python/SQLite
- **Study schedule**: Mon–Sat morning (oposición A1-01 GVA Técnico Superior), library preferred
- **Study window**: ~11:30–19:00 weekdays (stretchable +30min with fatigue cost)
- **Sunday**: Fully free (no studying, good for async code work)

---

## 🔴 CRITICAL RULES — DO NOT BREAK

### GVAdictos (Extreme Legal Rigor)

1. **NO invented legal content** — Every claim must cite BOE/DOGV/EUR-Lex official sources
2. **NO modifying originals** in `data/sources/leyes_originales/` — Only add new files
3. **ALL questions marked `requiere_revision=1`** if generated with AI help
4. **SQLite locking** — Never run multiple write ops in parallel; use 3-phase pattern
5. **EUR-Lex import** — Use `scripts/import_eurlex_direct.py` (not SPARQL) for direct URLs
6. **Validation findings** — Always update `topic_validation_findings` status when resolved
7. **NO copy/paste between Code + PRO** — Use GitHub raw.githubusercontent.com + .claude/ sync

---

## 📦 Recent Versions

| Component | Version | Status | Last Updated | Notes |
|-----------|---------|--------|--------------|-------|
| **GitHub CLI** | 2.94.0 | ✅ Active | 2026-06-17 | SSH auth, public repo |
| **EUR-Lex import** | 1.0 | ✅ Complete | 2026-06-17 | Carta UE, RGPD, Reglamento 2024/2509 (849 articles) |
| **Python codebase** | Current | ✅ Compiles | 2026-06-17 | No syntax errors |
| **SQLite schema** | Current | ✅ 80 laws | 2026-06-17 | 12,838 articles, 75 topics |

---

## 🗂️ Repository Structure

```
GVAdictos/                          ← GitHub: IsaacGaRos/GVAdictos (PUBLIC)
├── app.py                          ← Streamlit UI
├── db/gvadicto.sqlite              ← SQLite (TRACKED in git)
├── data/
│   ├── sources/
│   │   ├── leyes_originales/       ← Official downloads (DO NOT MODIFY)
│   │   │   ├── BOE/
│   │   │   ├── DOGV/
│   │   │   └── EURLEX/
│   │   ├── convocatorias/A1-01_2025/
│   │   │   └── a1_01_2025_topic_validation_audit.csv
│   │   └── drive_inventory/
│   └── processed/official_sources/ ← Converted texts (safe to change)
├── scripts/
│   ├── import_eurlex_direct.py     ← EUR-Lex download (3-phase pattern)
│   ├── audit_validation_findings.py ← Inspect hallazgos
│   ├── check_source_updates.py     ← Weekly watchdog (BOE/DOGV)
│   └── [other scripts]
├── src/
│   ├── core/db.py                  ← Schema, connection
│   ├── laws/importer.py            ← Parse articles
│   └── [other modules]
├── docs/
│   ├── CLAUDE_HANDOFF.md           ← Complete traspaso
│   ├── A1_LEGISLATION_AUDIT.md     ← Normativa audit
│   ├── CURRENT_STATUS.md           ← State snapshot
│   └── STUDY_INTERFACE_SPEC.md     ← Future UI design
├── .claude/                        ← SYNC CONTEXT (you are here)
│   ├── NEXT_CHAT_START_HERE.md
│   ├── MEMORY_COMPACT_DUMP.md      ← This file
│   ├── CURRENT_BASELINE.md
│   ├── RULES_DO_NOT_BREAK.md
│   ├── SYNC_CHECKLIST.md           ← NEW: automated sync protocol
│   └── LAST_SESSION_SNAPSHOT.md    ← NEW: what Code/PRO did last
└── [config, README, etc]
```

---

## 🔗 Critical Workflows

### Code (this chat) → GitHub → PRO

1. **Code works locally** → `git push origin branch-name`
2. **Code updates `.claude/LAST_SESSION_SNAPSHOT.md`** (2 min job)
3. **Code commits + pushes** to GitHub
4. **PRO joins** → reads `.claude/SYNC_CHECKLIST.md` → runs auto fetch script
5. **PRO reads `.claude/LAST_SESSION_SNAPSHOT.md`** → sees what Code did
6. **PRO proposes work** → Code implements → loop

---

## ⚙️ Build & Verification Commands

```bash
# Verify no syntax errors
python -m compileall app.py src scripts

# Quick DB stats
python -c "from src.core.db import connect; conn = connect(); print(conn.execute('SELECT COUNT(*) FROM laws').fetchone())"

# Run app
streamlit run app.py

# Check validation findings
python scripts/audit_validation_findings.py

# Push to GitHub
git push origin master
```

---

## 📝 Project-Specific Notes

### Architecture
- **Local-first** SQLite app + Streamlit UI
- **No external API** (except EUR-Lex downloads, handled locally)
- **Legal rigor**: All content traced to official sources

### Data flow
- Official sources → Downloaded to `data/sources/leyes_originales/`
- Parsed → Stored in SQLite
- Exported → Anki, CSV for study

### Ongoing work
- **29 open validation findings** (delimitación articulos, temas doctrinales, etc)
- **20 pilot questions** (all require_revision=1, need legal review)
- **Future**: study interface (anotaciones, Pomodoro, repetición espaciada)

---

## 🚨 Known Issues & Gotchas

### Past errors avoided
- ✅ EUR-Lex SPARQL sometimes fails → use direct URLs instead
- ✅ SQLite locks if multiple writes in parallel → use 3-phase pattern (download, convert, import separately)
- ✅ Database gets large (12K+ articles) → don't accidentally delete; track in git

### Current known limitations
- ⏳ 29 validation findings still open (requires manual review)
- ⏳ Study interface not yet built (spec exists)
- ⏳ Spaced repetition not implemented
- ⏳ Questions only from Ley 39/2015 (20 total)

---

## 💬 Communication Notes

**Code ↔ PRO sync**:
- Code writes to `.claude/LAST_SESSION_SNAPSHOT.md` (what I did)
- PRO reads `.claude/SYNC_CHECKLIST.md` (how to get latest)
- Both trust `.claude/*.md` as source of truth
- Minimize copy/paste; use GitHub URLs instead

---

## 🔄 Update Instructions

**After each Code session, run**:
```bash
cd C:\Users\isaac\Desktop\GVAdictos
git fetch origin && git pull origin master
python scripts/audit_validation_findings.py  # if touching validations
# ... work ...
git add .
git commit -m "message"
git push origin master

# THEN update .claude/ files:
# - .claude/LAST_SESSION_SNAPSHOT.md (what changed, next steps)
# - .claude/CURRENT_BASELINE.md (if new issues/fixes found)
git add .claude/
git commit -m "Update context for PRO sync"
git push origin master
```

**Time to update .claude/**: ~3 minutes

---

*This file is the immune system of Code + PRO collaboration. Keep it fresh, keep sync working.*
