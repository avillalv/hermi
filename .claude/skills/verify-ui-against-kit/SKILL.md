---
name: verify-ui-against-kit
description: "Check a built screen or component against the Hermi design kit, in ticket mode for UI steps. Runs the kit tests, collects screenshots and diffs for opus-reviewer, runs the copy lint, and lists the 05 states with their tests. Use after sonnet-coder finishes a UI step and before opus-reviewer."
---

# Verify a UI step against the kit

You verify. You do not fix. Send each failure back to `sonnet-coder` with the exact failing test or line.

Input: the step id and its `Kit:` line (a 05 section and a mockup, or "none, follow DESIGN-LANGUAGE.md section 11"). The kit is `app-buildout/phase-1-launch/design/`.

## 1. Is the kit test project there?

Run `grep -q '"test:kit"' package.json`. If it fails, WF-130 has not landed. Check the screen yourself and say so in your report:

- Start the app as in step 2. Open the mockup `design/screens/NN-*.html` (add `#dark` for dark) and the app screen in Playwright, at 390 by 844 with device scale factor 2, light and dark. A short node script is fine. Run `npx playwright install chromium` if the browser is missing.
- Save the four PNGs under `.autopilot/tmp/ui-<step id>/`, open them with Read next to `design/png/NN-*.png`, and list every visible difference.
- Skip steps 3 and 4. Do steps 5 to 8, and put the PNG paths in the report for `opus-reviewer`.

## 2. Start what is needed

If the Playwright config starts the app itself (a `webServer` entry), skip this. If both ports already answer, reuse that server. Otherwise start `npm run dev` in the background (the Bash tool's `run_in_background`, never the foreground) with `AI_PROVIDER=fake`, `SCHEDULER_ENABLED=false` and `AUTH_MODE=dev`. Poll for at most 120 seconds until `curl -s http://127.0.0.1:8100/health/live` answers and `curl -s -o /dev/null http://localhost:5173` succeeds. If either is still down after 120 seconds, report failure with the last 40 lines of the server log (the background command's output), stop the processes as in step 7 and stop there. The API uses port 8100 and the web app port 5173.

## 3. Run the kit tests

`npm run test:kit`, with a long timeout (up to 10 minutes) or in the background. WF-130 added three Playwright projects, all at 390 by 844, device scale factor 2, light and dark: `kit`, `kit-metrics` and `kit-parity`. The Playwright config has the exact scope.

- **Hard gates:** `kit-metrics` (computed styles of the `h-` components) and the component cases of `kit-parity`. One failure blocks the step.
- **Evidence only:** the screen-level `kit-parity` diffs and the screenshots. They go to `opus-reviewer`.

## 4. Collect the evidence

List absolute paths (`C:/Users/...`) for each screen, light and dark:

- the app screenshot and the diff PNG, under `test-results/` (or where WF-130's tests print them), newest first;
- the matching kit PNG: `app-buildout/phase-1-launch/design/png/NN-<screen>.png`, plus `NN-<screen>-dark.png` where it exists (03 and 07 only), or `components.png` for components;
- the diff ratio per screen.

Open one pair with Read to confirm the paths are right. Pass all of it to `opus-reviewer` in its brief.

## 5. Copy lint, lint and axe

- `node scripts/check-copy.mjs`, if the file exists (WF-007 adds it).
- `npm run lint` covers stylelint and jsx-a11y.
- axe: run the axe check the web e2e defines (search `axe` in `apps/web/e2e/`), light and dark. Zero serious or critical violations.

## 6. List the states

Open the screen's section in `05-ui-ux-spec.md` (named in the `Kit:` line, for example "6.5 Trips home") and read its `**States.**` paragraph. For each state (loading, empty, error, offline, limit, and any other it names), find the component test that renders it. Offline and error also need a Playwright test. A state with no test is a gap for the coder.

## 7. Clean up

Stop what you started and free the ports. In Git Bash:

```bash
for p in 8100 5173; do
  for pid in $(netstat -ano | tr -d '\r' | awk -v p=":$p" '$1=="TCP" && $2 ~ (p "$") && $4=="LISTENING" {print $5}' | sort -u); do
    MSYS_NO_PATHCONV=1 taskkill /PID "$pid" /T /F
  done
done
```

Then `netstat -ano | grep -E ':(8100|5173) '` must show no LISTENING line.

## 8. Report

Six lines at most: kit tests (pass or fail per project, or "not available yet"), copy lint, axe, states (n of n tested, gaps named), the evidence paths for `opus-reviewer`, and anything you could not run.
