# TradingHub

React/MUI frontend with historical strategy simulations and a Python backend. Apply personal workflow guides from the active Codex home; do not copy them into this repository.

## Working preferences

- Use short, plain-language code comments instead of new explanatory Markdown documents.
- Whenever a feature or bug fix is finished and verified, include a ready-to-copy commit message in the final handoff without waiting to be asked. Inspect the actual diff and scope the message to that work, excluding unrelated pending changes. Use a concise, action-oriented subject and add a short body only when useful. If verification is incomplete, label the message as a draft and state the remaining gap outside the message. Drafting a message does not authorize staging or committing.
- Before preparing a commit message or GitHub PR, inspect the relevant changes for obsolete or redundant tests and temporary files. Remove only clearly redundant or obsolete files within scope; retain distinct calculation, conversion, behavior, and accessibility coverage. Report what was removed or why tests were kept.
- Do not commit, push, deploy, install dependencies, or change permissions without explicit authorization.
- Strategy source snapshot: `C:\Users\kgsat\Documents\algo_trading-main\algo_trading-main`. Check its current contents before changing parameter visibility or simulation integration. It is a ZIP snapshot, not a Git checkout; do not assume it is synchronized with Annie's `algo_trading` repository or overwrite it automatically.

## Preserve during UI work

- Keep seven parameter columns at viewport widths of 1800px and above, native date controls, compact accessible help, and responsive wrapping.
- Preserve light/dark and glass/solid modes, distinguishable chart lines, and reduced-motion behavior. Full-screen transitions belong to explicit simulation runs, not tab changes.
- Keep financial surfaces readable. Do not animate chart data or metric values, change formulas or API units as styling work, or mix fictional previews with real results.
- Keep completed-run statistics and explanations tied to that run, not subsequently edited settings.

## Verification and handoff

- For reported clipping or spacing problems, inspect the actual affected edges at the reported viewport. Diagnose before another CSS change; tests and builds alone do not establish a visual fix. If rendering is unavailable, label the change visually unverified.
- Read primary design references before claiming inspiration; distinguish inspected layouts from unverified motion. Translate a concrete visual idea rather than only swapping colors.
- Use focused checks after each relevant change; run the affected regression suite and production build for substantive frontend changes. Do not repeat successful checks without a relevant change or new concern.
- Keep updates and commit descriptions concise: changed behavior, verification, and material gaps. Do not claim every feature is preserved without checking the affected behavior.

## Frontend commands

Run from `frontend` in Windows PowerShell:

- Start: `npm.cmd start` (port 3000 by default; check for an existing server first).
- Tests: `$env:CI='true'; npm.cmd test -- --watchAll=false --runInBand`.
- If Jest reports a temporary-cache permission error, add `--cacheDirectory=./node_modules/.cache/jest`; do not change permissions.
- Build: `npm.cmd run build`.

Use the existing dependencies. Frontend compilation does not verify the backend; distinguish fixture-based checks from real simulation verification.
