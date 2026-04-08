# Preview / Publish Fix PASS/FAIL

- Generated at: `2026-04-08T18:55:00Z`
- Reported broken job: `24981c05-f6c3-4933-bc56-93a6bdae4435`
- Fresh live replay job: `7b4cf12c-0903-4e68-8a07-8cf266f0001d`

| Requirement | Status | Evidence |
| --- | --- | --- |
| Published HTML rewrites root assets into job scope | PASS | `post_fix_published_html.html` contains `/published/24981c05-f6c3-4933-bc56-93a6bdae4435/assets/...` |
| Scoped published asset serves the generated app bundle | PASS | `post_fix_scoped_asset_head.txt` is the generated app JS, not CrucibAI's root app shell |
| Missing published assets return 404 instead of `index.html` | PASS | `local_route_verification.json` shows `missing_asset_status: 404` |
| Completed jobs expose a remote preview URL | PASS | `local_route_verification.json` shows `preview_url` and `deploy_url` populated |
| Fresh live production golden path stays green after the fix | PASS | `live_post_fix/PASS_FAIL.md` shows all live requirements passing, including `published_assets_scoped` |
| Golden-path workspace UX stops misreporting polling as reconnecting | PASS | `golden_path_ux/PASS_FAIL.md` includes the new preview fallback and polling-label checks |

## Root Cause

- Published job HTML was served with absolute `/assets/...` paths.
- Browsers then fetched CrucibAI's root frontend bundle instead of the generated app bundle.
- The workspace preview pane also relied on `job.preview_url`, but jobs did not reliably persist one.
- SSE fallback was healthy, but the UI still labeled it as `Reconnecting`.

## Fix

- The published app route now rewrites HTML asset paths into `/published/{job_id}/...`.
- Missing asset requests now return `404` instead of falling back to `index.html`.
- The job API enriches completed jobs with `preview_url`, `published_url`, and `deploy_url` when a published dist exists.
- The workspace preview falls back to the published app URL.
- Polling fallback is labeled as `Polling` instead of implying the run is broken.
