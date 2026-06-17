# 🔄 Sync Checklist — Claude PRO Auto-Sync Protocol

**Last updated**: 2026-06-17T21:00:00 UTC  
**For**: Claude PRO starting a new session

---

## ⚡ Quick Start (PRO — Copy/Paste This)

When you join GVAdictos:

```python
# Step 1: Fetch latest Code's work
web_fetch('https://api.github.com/repos/IsaacGaRos/GVAdictos/commits?per_page=5')
# ↑ Shows 5 most recent commits

# Step 2: Read what Code did last session
web_fetch('https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/LAST_SESSION_SNAPSHOT.md')
# ↑ Explains: what changed, what needs review, what's next

# Step 3: Check current rules
web_fetch('https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/RULES_DO_NOT_BREAK.md')
# ↑ Critical: don't break these

# Step 4: See project state
web_fetch('https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/CURRENT_BASELINE.md')
# ↑ What works, what's broken, what's next

# Step 5: See memory
web_fetch('https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/MEMORY_COMPACT_DUMP.md')
# ↑ Architecture, workflows, gotchas
```

After these 5 fetches, you have **full context**. Then say:

> "I've synced with Code's latest work. What should I focus on?"

---

## 📋 Auto-Sync Checklist

PRO should verify (in order):

- [ ] **GitHub commits** — Fetch API shows latest commits
- [ ] **Session snapshot** — LAST_SESSION_SNAPSHOT.md is recent (< 1 week)
- [ ] **No blockers** — RULES_DO_NOT_BREAK.md shows no violations
- [ ] **Build status** — CURRENT_BASELINE.md shows ✅ all systems
- [ ] **Memory current** — MEMORY_COMPACT_DUMP.md timestamp is fresh

**If ANY check fails:**
- ❌ Snapshot is stale? Ask Code: "Your last update was X days ago, can you update .claude/ files?"
- ❌ Rules broken? Review RULES_DO_NOT_BREAK.md + CURRENT_BASELINE.md before proceeding
- ❌ Build broken? Check if Code noted it in CURRENT_BASELINE.md (under "Known issues")

---

## 🔗 Key URLs (Bookmark These)

| File | URL |
|------|-----|
| **Last Session Snapshot** | https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/LAST_SESSION_SNAPSHOT.md |
| **Rules** | https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/RULES_DO_NOT_BREAK.md |
| **Baseline** | https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/CURRENT_BASELINE.md |
| **Memory** | https://raw.githubusercontent.com/IsaacGaRos/GVAdictos/master/.claude/MEMORY_COMPACT_DUMP.md |
| **Recent commits (API)** | https://api.github.com/repos/IsaacGaRos/GVAdictos/commits?per_page=10 |
| **All files (browser)** | https://github.com/IsaacGaRos/GVAdictos (browse from here) |

---

## 🎯 Typical PRO Session Flow

1. **Start session** → Run 5 web_fetch commands above
2. **Read LAST_SESSION_SNAPSHOT.md** → Understand what Code did
3. **Ask Code**: "I see you did X. Next I'll work on Y — does that fit?"
4. **Code responds** → Confirms or adjusts plan
5. **Code works** → Updates LAST_SESSION_SNAPSHOT.md, pushes
6. **You read** → See changes, propose refinements
7. **Loop**

---

## ⏰ Update Cadence

| When | Who | What |
|------|-----|------|
| After each Code session | Code | Update `.claude/LAST_SESSION_SNAPSHOT.md` |
| Before PRO session | PRO | Fetch 5 URLs above (2 min) |
| If bug found | Whoever finds it | Add to RULES_DO_NOT_BREAK.md |
| Weekly (or as needed) | Code | Update CURRENT_BASELINE.md |

---

## 🚀 Why This Works

- ✅ PRO never guesses what Code did (snapshot says it)
- ✅ No copy/paste needed (URLs handle it)
- ✅ Rules stay fresh (both chats see same rules)
- ✅ GitHub is source of truth (always up-to-date)
- ✅ Minimal overhead (5 web_fetch calls = 2 minutes)

---

## 🆘 Troubleshooting

**PRO fetches old snapshot?**
→ GitHub cached it. Refresh: use `?v=<timestamp>` or ask Code to update.

**Rules aren't being followed?**
→ Check RULES_DO_NOT_BREAK.md. If rule is new, Code should have added it.

**Not sure what changed?**
→ Fetch API commits URL, see diffs in GitHub UI.

**Code didn't update .claude/ files?**
→ Message: "Hey, your last .claude/ update was X days ago, can you refresh?"

---

**Ready?** Fetch the 5 URLs above, read the snapshot, then jump in.
