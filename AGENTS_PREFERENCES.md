# Maintainer preferences (for AI / human agents)

Read this alongside `AGENTS.md`. It records how the maintainer works with this repo so agents can match expectations.

## No pre-merge testing

The maintainer **does not** run a separate local or staging test pass before merging. PRs are **merged to `main` as the normal path**; **validation happens after deploy** (e.g. production or the next environment that runs the new build).

Do not assume the maintainer will “try it” before merge, and do not block on “wait for manual test” unless they explicitly ask for that.

## Merge completed work

When a batch of changes is ready, **open a PR and merge it** (e.g. `gh pr merge` or the GitHub UI) so it lands on `main` and deploy can pick it up. Avoid leaving branches / PRs in “ready but unmerged” state unless the maintainer asked to hold it.

## One topic per PR

Prefer **one focused PR per feature or fix** (separate branches), not one giant PR with many unrelated changes. The maintainer merges each PR to test on `main` incrementally.

## If something is unclear

When in doubt, follow `AGENTS.md` and the cloud-agent rules in the Cursor environment; this file only adds **process** preferences, not code standards.
