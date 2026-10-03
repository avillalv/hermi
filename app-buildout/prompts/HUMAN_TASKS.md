# Owner-only tasks

Steps only the owner can do: accounts, keys, payments, legal review, Mac builds, App Store. The
orchestrator adds to this list and never blocks on it. Keep it in the order the owner should do them.

| # | Task | Needed by prompt | Status |
|---|---|---|---|
| 1 | Create the GitHub repository with branch protection on `main` that lets the orchestrator merge once CI passes | 01 | Open |

Add rows below as prompts discover them. Each row says exactly where the key or setting goes (for
example "add `ANTHROPIC_API_KEY` to Render env group `hermi-staging`").
