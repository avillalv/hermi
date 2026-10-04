---
name: autopilot-status
description: "Report how the Hermi autopilot build is going. Use when someone asks about build progress, which prompt is running, the pull request, whether the run is stopped or paused, or what the owner must do. Read-only."
allowed-tools:
  - "Bash(node scripts/autopilot/status.mjs)"
  - "Bash(node scripts/autopilot/status.mjs *)"
---

# Autopilot status

1. Run `node scripts/autopilot/status.mjs`. It prints the state without loading the logs.
2. Answer in five lines, no more:
   1. **Now:** the current unit and the phase `state.json` records (`plan`, `ticket`, `ship`, `ci`, `merged` or `stopped`; the final session also shows as `ship`, and a ci-fix session as `ci`), and the step if there is one.
   2. **PR:** the link and its state (draft, ready or merged).
   3. **Progress:** units done of the total, as the script prints them.
   4. **Last activity:** when, and what, in one line.
   5. **Stop or pause:** the reason and the owner action, or "none".
3. If the script is missing or fails, say so in one line and use only these small reads:
   - the Status column of the unit rows in `app-buildout/prompts/PROGRESS.md` (`grep -E '^\| (S[0-9]|[0-9]{2}|FINAL) \|' app-buildout/prompts/PROGRESS.md`);
   - `gh pr list --state open --json number,title,url,isDraft`;
   - `.autopilot/stop.json`, if it exists;
   - the name and modified time of the newest file in `.autopilot/logs/` (`ls -t .autopilot/logs | head -1`).

Never open or print a whole log file. The logs in `.autopilot/logs/` are large JSON lines. Never change anything. How to start, stop and resume the run: `knowledge/autopilot.md`.
