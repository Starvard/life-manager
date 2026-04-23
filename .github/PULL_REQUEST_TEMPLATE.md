## Summary

## Release label

**You do not need to bump a version by hand.** After merge, **Deploy to Fly.io** sets the running app’s label to **pr&lt;number&gt;** (the GitHub PR that landed that commit) and shows it on Home and in `GET /healthz`. Pushes to `main` without a PR get a **short git SHA** instead. Override anytime with the `LM_APP_VERSION` environment variable if you need a custom label.
