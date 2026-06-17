# 🚫 Rules DO NOT BREAK

**Last updated**: 2026-06-17T21:00:00 UTC  
**Project**: GVAdictos  
**Purpose**: Prevent critical errors from repeating. CONSULT THIS BEFORE MODIFYING CODE.

---

## 🔴 SACRED PATTERNS — ZERO TOLERANCE

### 1. **NO Invented Legal Content**
- ❌ NEVER claim a norma is "vigente" without official BOE/DOGV/EUR-Lex source
- ❌ NEVER invent articles or text from memory
- ❌ NEVER use academic PDFs (Autentica, EraCEF) as definitive sources

**Why**: Oposición exam questions require 100% legal accuracy. Wrong source = exam failure.

**Check before commit**:
```python
# If you're adding a question or claim:
grep -r "requires_revision" questions  # Should be 1 if AI-generated
# Verify source in DB:
SELECT * FROM questions WHERE id = X; -- Check 'fuente' field
```

---

### 2. **DO NOT Modify Originals in `data/sources/leyes_originales/`**
- ❌ NEVER edit `.html`, `.txt`, `.md` in that folder
- ✅ Only ADD new files (new EUR-Lex downloads, etc)
- ✅ Processed versions go in `data/processed/official_sources/`

**Why**: Originals are audit trail. If you need to modify, create new version in `processed/`.

**Check before commit**:
```bash
git diff data/sources/leyes_originales/  # Should show only ADDITIONS, not modifications
```

---

### 3. **SQLite: Use 3-Phase Pattern for EUR-Lex Import**
- ❌ NEVER hold connection open while calling `import_law()`
- ✅ Phase 1: Download + update source_documents (single conn, commit)
- ✅ Phase 2: Convert + import (separate, no open conn)
- ✅ Phase 3: Update findings (single conn, commit)

**Why**: SQLite locks if multiple writes overlap. 3-phase avoids "database is locked" error.

**Example** (see `scripts/import_eurlex_direct.py`):
```python
# WRONG:
with connect() as conn:
    update_row()
    import_law()  # ← LOCKS!

# RIGHT:
with connect() as conn:
    update_row()
    conn.commit()
# Connection CLOSED here
for item in pending:
    import_law(item)  # ← OK, no lock
with connect() as conn:
    mark_resolved()
```

---

### 4. **All AI-Generated Questions Must Mark `requiere_revision=1`**
- ❌ NEVER set `requiere_revision=0` for AI-generated questions
- ✅ Even if you review it, mark=1 so human lawyer double-checks
- ✅ Only `requiere_revision=0` for fully human-written, lawyer-approved

**Why**: Legal liability. AI can be wrong; mark it for human review.

**Check before commit**:
```sql
SELECT COUNT(*) FROM questions WHERE requiere_revision=0 AND etiquetas LIKE '%generado%';
-- Should return 0 (no AI questions without revision flag)
```

---

### 5. **EUR-Lex Import: Use Direct URLs, Never Trust SPARQL Alone**
- ❌ NEVER rely only on SPARQL for EUR-Lex discovery
- ✅ Use `scripts/import_eurlex_direct.py` with verified URLs
- ✅ If URL 404s, investigate CELEX ID first (not alternate sources)

**Why**: EUR-Lex SPARQL is incomplete for some docs. Direct download is reliable.

**Check before commit**:
```bash
# If importing new EUR-Lex:
curl -I "https://eur-lex.europa.eu/legal-content/ES/TXT/XHTML/?uri=CELEX:XXXXX"
# Should return 200 OK, not 404
```

---

### 6. **Always Update `topic_validation_findings` When Resolving Issues**
- ❌ NEVER leave status='abierto' after fixing a topic
- ✅ Set `status='resuelto'` in topic_validation_findings after validation
- ✅ Update timestamp

**Why**: PRO and future chats need to know what's done. Stale status causes duplicate work.

**Check before commit**:
```sql
SELECT COUNT(*) FROM topic_validation_findings WHERE status='abierto';
-- Should decrease with each resolved topic
```

---

### 7. **NO Copy/Paste Between Code + PRO**
- ❌ NEVER copy task details, code, or output from one chat to another
- ✅ Use GitHub URLs: raw.githubusercontent.com
- ✅ Use `.claude/` files for sync
- ✅ Communicate via `.claude/LAST_SESSION_SNAPSHOT.md`

**Why**: Copy/paste breaks sync. If Code pushes, PRO reads from GitHub = always fresh.

**Check before commit**:
```bash
# If you're telling PRO something, did you PUSH it to GitHub first?
git log --oneline -1  # Should show your latest commit
git push origin master  # Then PRO can fetch it
```

---

## 🟡 PROJECT-SPECIFIC RULES

### 8. **No Parallel SQLite Writes**
- ❌ NEVER run `check_source_updates.py` + `import_eurlex_direct.py` in parallel
- ✅ Always sequential: one watchdog, wait for it to finish, then import

**Why**: SQLite can lock; parallel writes = "database is locked" crash.

---

### 9. **Validation Rigor for Questions**
- Source must be in SQLite (`laws` table)
- Article ID must exist (`articles` table)
- Both `law_id` and `article_id` required (not null)
- If topic not yet validated: DON'T generate questions for it

**Check before generating questions**:
```sql
SELECT topic_id, validation_status FROM topics WHERE topic_id = ?;
-- Should be 'validado' or 'requiere_revision' NOT 'pendiente_de_validacion'
```

---

### 10. **Never Assume Norma Vigencia**
- A law in `data/sources/` is NOT automatically vigente
- Check DOGV/BOE publication dates
- Check if explicitly derogated/modified
- Include version date in question/explanation

---

## ✅ Rule Checking Checklist

**BEFORE EVERY COMMIT, verify**:

- [ ] No invented legal content (grep for "probably", "likely", "seems")
- [ ] No modifications in `data/sources/leyes_originales/` (only additions)
- [ ] `topic_validation_findings` updated if hallazgos resolved
- [ ] AI questions marked `requiere_revision=1`
- [ ] EUR-Lex URLs tested (curl -I, should be 200 OK)
- [ ] No parallel SQLite writes running
- [ ] `.claude/` files updated (especially LAST_SESSION_SNAPSHOT.md)
- [ ] Commit message references issue/finding being resolved
- [ ] GitHub push completed before PRO session starts

**If ANY check fails**: ❌ **STOP.** Review the rule above, fix, re-test, then commit.

---

## 🔄 How to Update This File

**If a new critical error pattern is discovered**:

1. Create new section: `### N. [Clear Title]`
2. List ❌ wrong patterns and ✅ right patterns
3. Add "Why:" explanation (reference, impact)
4. Add SQL/bash check example
5. Add to **Rule Checking Checklist** above
6. Update timestamp at top
7. Commit: `git commit -m "Add rule N: [title]"`

**Time to add a rule**: ~5 minutes

---

## 📋 Rule History

| Rule | Date Added | Reason |
|------|-----------|--------|
| No invented legal | 2026-06-17 | Extreme legal rigor required |
| No modify originals | 2026-06-17 | Audit trail integrity |
| SQLite 3-phase | 2026-06-17 | EUR-Lex import locking issues |
| AI questions revision=1 | 2026-06-17 | Legal liability |
| EUR-Lex direct URLs | 2026-06-17 | SPARQL unreliability |
| topic_validation_findings sync | 2026-06-17 | Code + PRO coordination |
| No copy/paste sync | 2026-06-17 | GitHub-based sync protocol |

---

*This file is the "immune system" against repeating past mistakes. Consult it before every commit.*  
*Both Code and PRO check this. Violations block commits.*
