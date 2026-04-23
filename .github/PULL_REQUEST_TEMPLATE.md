## Summary

## Release label (optional)

Bumping the **single** release label in `version.txt` (for example from `0.0.0-dev` to `1.2.0` or a dated tag like `2026.04.23`) is how Home and `/healthz` know what is deployed after you merge. Skip the bump for tiny or internal changes; set `LM_APP_VERSION` in the host environment to override the file (for example a CI build number).

- [ ] I updated `version.txt` for a named release, or
- [ ] N/A (no new deploy label needed)
