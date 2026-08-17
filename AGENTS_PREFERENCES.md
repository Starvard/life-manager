# Maintainer preferences (for AI / human agents)

Read this alongside `AGENTS.md`. It records how the maintainer works with this repo so agents can match expectations.

## No pre-merge testing

The maintainer **does not** run a separate local or staging test pass before merging. PRs are **merged to `main` as the normal path**; **validation happens after deploy** (e.g. production or the next environment that runs the new build).

Do not assume the maintainer will “try it” before merge, and do not block on “wait for manual test” unless they explicitly ask for that.

## Merge completed work

When a batch of changes is ready, **open a PR and merge it** (e.g. `gh pr merge` or the GitHub UI) so it lands on `main` and deploy can pick it up. Avoid leaving branches / PRs in “ready but unmerged” state unless the maintainer asked to hold it.

## One topic per PR

Prefer **one focused PR per feature or fix** (separate branches), not one giant PR with many unrelated changes. The maintainer merges each PR to test on `main` incrementally.

## PWA / phone “still the old app”

If a phone still shows an old budget UI or wrong numbers after deploy: the installed web app (standalone) can be sticky. The Budget page sets **no-cache** headers and the client **re-fetches the report** on every load, but a full **Safari/Chrome** refresh or “pull to refresh” on the *non*-standalone tab may be needed. Check **build: pr#** (or version) on the Budget subtitle after deploy—if it did not change, the device is not loading the new HTML.

## Weekly meals (Recipes tab)

Keep the existing Recipes tab format (Menu + Grocery lists — not a per-day calendar). When asked for a new week, write a **completely new** plan in `services/easy_weekly_seed.py` and bump `SEED_ID` (and `WEEK_KEY`) so it applies once on startup.

Household rules:
- Breakfast: a small pool (usually 2 easy, high-protein options)
- Lunch: leftovers from dinner
- Dinner: 5 meals, each covering dinner + next-day lunch for **2 adults + 1 kid** (~**5–6 servings**); pack leftovers before sitting down
- Snacks: grab-and-go list (no full recipes required)
- Grocery: amounts on every row; replace last week’s specials; **do not uncheck** pantry staples already marked as have

## If something is unclear

When in doubt, follow `AGENTS.md` and the cloud-agent rules in the Cursor environment; this file only adds **process** preferences, not code standards.
