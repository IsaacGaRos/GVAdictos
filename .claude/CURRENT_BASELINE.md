# âœ… Current Baseline

> Nota 2026-06-18: este baseline es historico. Para el estado actual usar `docs/CLAUDE_HANDOFF.md` y `.claude/NEXT_CHAT_START_HERE.md`. Recuento actual: 81 leyes, 11509 articulos, 75 temas, 742 topic_sources.

**Last updated**: 2026-06-17T21:00:00 UTC
**Project**: GVAdictos
**Last verified**: 2026-06-17 (today)

---

## ðŸŸ¢ What's Working (Confirmed)

- âœ… **Python codebase**: Compiles without errors (`python -m compileall`)
- âœ… **SQLite database**: 80 laws, 12,838 articles, schema intact
- âœ… **EUR-Lex import**: 3 new sources (Carta UE, RGPD, Reglamento 2024/2509)
- âœ… **GitHub integration**: SSH authenticated, public repo, 2 commits
- âœ… **Article parsing**: 849 new articles imported successfully
- âœ… **Validation findings**: 3 EUR-Lex findings resolved
- âœ… **Documentation**: COLLABORATION.md, GITHUB_SETUP.md ready
- âœ… **Code + PRO sync**: Infrastructure in place (SYNC_CHECKLIST.md)
- âœ… **Scripts**: `audit_validation_findings.py`, `import_eurlex_direct.py` tested

---

## ðŸŸ¡ What's NOT Working / Pending Issues

### Known bugs (critical)
- None currently

### Known bugs (non-critical)
- None currently

### Incomplete features
- â³ **23 open validation findings** â€” need manual review & mapping
  - 8: DelimitaciÃ³n de artÃ­culos (select specific articles per topic)
  - 2: Temas doctrinales (need matrix, not just law refs)
  - 19: Otros (reglamentarios, competencias sectoriales)
  - **Blocker for**: Expanding questions beyond 20 pilot

- âœ… **Study interface Phase 2.1** â€” Navigator tab exists in Streamlit
  - Features: Anotaciones, Pomodoro, version comparison
  - **Impact**: Medium (planned for later phase)

- â³ **Spaced repetition** â€” Not implemented
  - **Impact**: Medium (planned for later phase)

- â³ **Question bank expansion** â€” Only 20 pilot Qs from Ley 39/2015
  - **Blocker**: Waiting for validation findings resolution
  - **Impact**: High (essential for study)

### Performance issues (if any)
- None detected at current scale (SQLite ~150MB is fine)

---

## ðŸ”¨ Last Build Status

| Aspect | Status | Details |
|--------|--------|---------|
| **Last build date** | 2026-06-17 | Today (EUR-Lex import session) |
| **Build result** | âœ… SUCCESS | All 3 EUR-Lex sources imported |
| **Output generated** | 849 articles | From Carta UE (54) + RGPD (99) + Reglamento (696) |
| **Installation path** | `data/sources/leyes_originales/EURLEX/` | 3 HTML files, ~2.9 MB |
| **Verified** | âœ… Yes | `python -m compileall` passed, DB stats confirm |

---

## ðŸ“Š Last Runtime Verification

**Date**: 2026-06-17 21:00 UTC
**Test scenario**: EUR-Lex import + GitHub sync
**Outcome**: âœ… PASS

**Details**:
```
1. Downloaded 3 EUR-Lex sources (direct URL, no SPARQL)
2. Converted XHTML â†’ TXT â†’ SQLite articles
3. Updated topic_validation_findings status
4. Pushed to GitHub (2 commits)
5. Verified syntax: python -m compileall âœ…
6. Verified DB: SELECT COUNT(*) FROM articles = 12,838 âœ…
7. Verified GitHub: gh repo view shows PUBLIC âœ…
```

**KPI results**:
- Import speed: ~2 min per source (good)
- Error rate: 0 (clean import)
- DB size: ~150 MB (healthy for SQLite)
- GitHub latency: <1 sec per push (good)

---

## ðŸ” Config/Dependencies

### Runtime environment
- **Language**: Python 3.9+ (required by Streamlit)
- **Framework/Runtime**: Streamlit (web UI), SQLite3 (database)
- **Dependencies**: See `requirements.txt` (NumPy, pandas, requests, etc)

### Build configuration
- **Build target**: Local app (Streamlit) + SQLite database
- **Build command**: `python -m compileall app.py src scripts` (verify syntax)
- **Run command**: `streamlit run app.py` (start web UI)

### File system
- **Source path**: `C:\Users\isaac\Desktop\GVAdictos\`
- **Repo**: https://github.com/IsaacGaRos/GVAdictos (GitHub, PUBLIC)
- **Database**: `db/gvadicto.sqlite` (tracked in git)
- **Data**: `data/sources/leyes_originales/` (official downloads)
- **Scripts**: `scripts/*.py` (import, audit, watchdog)
- **Context**: `.claude/*.md` (sync protocol)

---

## ðŸš¨ Critical Alerts

**IF ANY OF THESE ARE TRUE, STOP AND REVIEW BEFORE PROCEEDING**:

- âŒ Last build was more than 2 weeks ago â†’ âœ… Today (fresh)
- âŒ A critical bug is marked "In progress" with no recent activity â†’ âœ… None open
- âŒ Build paths have changed â†’ âœ… Stable
- âŒ GitHub repo is out of sync â†’ âœ… Synced (2 commits, master)
- âŒ Validation findings blocking work â†’ âš ï¸ 23 open (but not critical for first Study UI slices)
- âŒ Database corrupted or missing â†’ âœ… Intact, 12,838 articles confirmed

**Current status**: âœ… **GREEN** â€” All systems nominal

---

## ðŸ“ How to Update This File

**After each task or session**:

1. **Update timestamp** at top
2. **Add completed work** to "What's Working"
3. **If new issues found**, add to appropriate section
4. **If issues resolved**, move from "NOT Working" to "Working"
5. **Update "Last Build Status"** with latest results
6. **Update "Critical Alerts"** section
7. **Commit to GitHub**

**Template for new issue**:
```
- â³ **[Feature/Bug name]** â€” [1-2 sentence description]
  - **Blocker for**: [What depends on this]
  - **Impact**: Low/Medium/High
```

**Time to update**: ~3 minutes per session

---

*This is the "current mirror" â€” always accurate = saves hours of debugging in future chats.*
*Keep it fresh. Both Code and PRO check this before deciding what to work on.*
