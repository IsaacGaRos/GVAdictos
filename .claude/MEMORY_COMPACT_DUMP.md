# ðŸ§  Memory Compact Dump

> Nota 2026-06-18: este dump es historico. Para el estado actual usar `docs/CLAUDE_HANDOFF.md` y `.claude/NEXT_CHAT_START_HERE.md`. Recuento actual: 81 leyes, 11509 articulos, 75 temas, 742 topic_sources.

**Last updated**: 2026-06-17T21:00:00 UTC  
**Project**: GVAdictos  
**Status**: GitHub integration + EUR-Lex import COMPLETE

---

## ðŸ‘¤ Work Context (Isaac)

- **Location**: Paterna/Tavernes Blanques, Valencia, ES (Europe/Madrid timezone)
- **Technical skills**: C#/.NET, DLL modules, GitHub, oposiciÃ³n prep, Python/SQLite
- **Study schedule**: Monâ€“Sat morning (oposiciÃ³n A1-01 GVA TÃ©cnico Superior), library preferred
- **Study window**: ~11:30â€“19:00 weekdays (stretchable +30min with fatigue cost)
- **Sunday**: Fully free (no studying, good for async code work)

---

## ðŸ”´ CRITICAL RULES â€” DO NOT BREAK

### GVAdictos (Extreme Legal Rigor)

1. **NO invented legal content** â€” Every claim must cite BOE/DOGV/EUR-Lex official sources
2. **NO modifying originals** in `data/sources/leyes_originales/` â€” Only add new files
3. **ALL questions marked `requiere_revision=1`** if generated with AI help
4. **SQLite locking** â€” Never run multiple write ops in parallel; use 3-phase pattern
5. **EUR-Lex import** â€” Use `scripts/import_eurlex_direct.py` (not SPARQL) for direct URLs
6. **Validation findings** â€” Always update `topic_validation_findings` status when resolved
7. **NO copy/paste between Code + PRO** â€” Use GitHub raw.githubusercontent.com + .claude/ sync

---

## ðŸ“¦ Recent Versions

| Component | Version | Status | Last Updated | Notes |
|-----------|---------|--------|--------------|-------|
| **GitHub CLI** | 2.94.0 | âœ… Active | 2026-06-17 | SSH auth, public repo |
| **EUR-Lex import** | 1.0 | âœ… Complete | 2026-06-17 | Carta UE, RGPD, Reglamento 2024/2509 (849 articles) |
| **Python codebase** | Current | âœ… Compiles | 2026-06-17 | No syntax errors |
| **SQLite schema** | Current | âœ… 80 laws | 2026-06-17 | 12,838 articles, 75 topics |

---

## ðŸ—‚ï¸ Repository Structure

```
GVAdictos/                          â† GitHub: IsaacGaRos/GVAdictos (PUBLIC)
â”œâ”€â”€ app.py                          â† Streamlit UI
â”œâ”€â”€ db/gvadicto.sqlite              â† SQLite (TRACKED in git)
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ sources/
â”‚   â”‚   â”œâ”€â”€ leyes_originales/       â† Official downloads (DO NOT MODIFY)
â”‚   â”‚   â”‚   â”œâ”€â”€ BOE/
â”‚   â”‚   â”‚   â”œâ”€â”€ DOGV/
â”‚   â”‚   â”‚   â””â”€â”€ EURLEX/
â”‚   â”‚   â”œâ”€â”€ convocatorias/A1-01_2025/
â”‚   â”‚   â”‚   â””â”€â”€ a1_01_2025_topic_validation_audit.csv
â”‚   â”‚   â””â”€â”€ drive_inventory/
â”‚   â””â”€â”€ processed/official_sources/ â† Converted texts (safe to change)
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ import_eurlex_direct.py     â† EUR-Lex download (3-phase pattern)
â”‚   â”œâ”€â”€ audit_validation_findings.py â† Inspect hallazgos
â”‚   â”œâ”€â”€ check_source_updates.py     â† Weekly watchdog (BOE/DOGV)
â”‚   â””â”€â”€ [other scripts]
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ core/db.py                  â† Schema, connection
â”‚   â”œâ”€â”€ laws/importer.py            â† Parse articles
â”‚   â””â”€â”€ [other modules]
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ CLAUDE_HANDOFF.md           â† Complete traspaso
â”‚   â”œâ”€â”€ A1_LEGISLATION_AUDIT.md     â† Normativa audit
â”‚   â”œâ”€â”€ CURRENT_STATUS.md           â† State snapshot
â”‚   â””â”€â”€ STUDY_INTERFACE_SPEC.md     â† Future UI design
â”œâ”€â”€ .claude/                        â† SYNC CONTEXT (you are here)
â”‚   â”œâ”€â”€ NEXT_CHAT_START_HERE.md
â”‚   â”œâ”€â”€ MEMORY_COMPACT_DUMP.md      â† This file
â”‚   â”œâ”€â”€ CURRENT_BASELINE.md
â”‚   â”œâ”€â”€ RULES_DO_NOT_BREAK.md
â”‚   â”œâ”€â”€ SYNC_CHECKLIST.md           â† NEW: automated sync protocol
â”‚   â””â”€â”€ LAST_SESSION_SNAPSHOT.md    â† NEW: what Code/PRO did last
â””â”€â”€ [config, README, etc]
```

---

## ðŸ”— Critical Workflows

### Code (this chat) â†’ GitHub â†’ PRO

1. **Code works locally** â†’ `git push origin branch-name`
2. **Code updates `.claude/LAST_SESSION_SNAPSHOT.md`** (2 min job)
3. **Code commits + pushes** to GitHub
4. **PRO joins** â†’ reads `.claude/SYNC_CHECKLIST.md` â†’ runs auto fetch script
5. **PRO reads `.claude/LAST_SESSION_SNAPSHOT.md`** â†’ sees what Code did
6. **PRO proposes work** â†’ Code implements â†’ loop

---

## âš™ï¸ Build & Verification Commands

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

## ðŸ“ Project-Specific Notes

### Architecture
- **Local-first** SQLite app + Streamlit UI
- **No external API** (except EUR-Lex downloads, handled locally)
- **Legal rigor**: All content traced to official sources

### Data flow
- Official sources â†’ Downloaded to `data/sources/leyes_originales/`
- Parsed â†’ Stored in SQLite
- Exported â†’ Anki, CSV for study

### Ongoing work
- **23 open validation findings** (delimitaciÃ³n articulos, temas doctrinales, etc)
- **20 pilot questions** (all require_revision=1, need legal review)
- **Current product focus**: study interface. Phase 2.1 navigator exists; next is minimal annotations, then AI doubt action on selected text, Pomodoro and repeticiÃ³n espaciada.

---

## ðŸš¨ Known Issues & Gotchas

### Past errors avoided
- âœ… EUR-Lex SPARQL sometimes fails â†’ use direct URLs instead
- âœ… SQLite locks if multiple writes in parallel â†’ use 3-phase pattern (download, convert, import separately)
- âœ… Database gets large (12K+ articles) â†’ don't accidentally delete; track in git

### Current known limitations
- â³ 29 validation findings still open (requires manual review)
- â³ Study interface not yet built (spec exists)
- â³ Spaced repetition not implemented
- â³ Questions only from Ley 39/2015 (20 total)

---

## ðŸ’¬ Communication Notes

**Code â†” PRO sync**:
- Code writes to `.claude/LAST_SESSION_SNAPSHOT.md` (what I did)
- PRO reads `.claude/SYNC_CHECKLIST.md` (how to get latest)
- Both trust `.claude/*.md` as source of truth
- Minimize copy/paste; use GitHub URLs instead

---

## ðŸ”„ Update Instructions

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
