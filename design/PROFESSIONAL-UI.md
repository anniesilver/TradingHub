# TradingHub professional workspace

Target: TradingHub. Scheduler is a design reference, not the implementation target.

## Audit and direction

The React 18 / Material UI 5 frontend is a historical backtest workspace, not currently a prediction product. Four strategy choices feed a shared form and simulation service. Results are adapted into Recharts performance, margin, cash, premium/interest, and log views. The Python service depends on market data and an external strategy engine. It does not expose market-data freshness, source time zone, or session metadata; the interface must not invent those signals.

The previous eight-column parameter grid clipped long labels and date inputs. The 280px permanent navigation did not reflow on narrow screens. Hardcoded light tooltips, IV cards, and log surfaces conflicted with a coherent dark theme. Settings could change while charts still described the previous run, without an explicit warning. The low-drawdown caption implied future stability.

Adapted from Scheduler's `Application.html` and `design/UI-DIRECTION.md` / `design/RESEARCH-AND-DESIGN.md`: local glass navigation, recessed controls, fine borders, bounded opacity/transform transitions, and explicit accessibility preferences. TradingHub uses navy/graphite/slate instead of Scheduler's more expressive plum/lilac palette. Dense financial surfaces remain opaque. No new fonts, animation libraries, or continuous effects are downloaded. The reference source/docs were inspected; Scheduler was not visually validated in this pass.

## First-pass TODO

- [x] Centralize palette, typography, radii, and common MUI component treatments.
- [x] Reflow strategy navigation and parameter controls; keep every parameter accessible.
- [x] Add a native, keyboard-operable advanced disclosure, initially open to preserve existing workflows.
- [x] Preserve existing percentage conversions, request values, symbol-per-strategy behavior, and calculations.
- [x] Label the workspace and outputs as historical/hypothetical, not live or forecasts.
- [x] Snapshot the successful run's inputs and client completion time; warn when settings differ.
- [x] State that source freshness/session/time-zone metadata is unavailable.
- [x] Add a skip link, visible focus, larger help targets, reduced-motion and solid-surface controls.
- [x] Remove series interpolation animations; connect recorded points linearly rather than with smoothed curves.
- [x] Keep glass out of charts; update hardcoded light IV/log/tooltip surfaces.
- [x] Remove predictive stability language from drawdown commentary without changing the formula.
- [ ] Validate production data/result charts against Annie's running backend (not available locally).

## Backlog requiring a separate pass

1. Confirm backend support for Enhanced Cashflow and formalize strategy-specific parameter groups.
2. Add date/range validation and repair the existing recent-data retry closure, separately from styling.
3. Handle concurrent request cancellation so late responses cannot replace another strategy's results.
4. Expose source timestamps, market sessions, source time zones, and feed latency through the API before adding freshness badges.
5. Confirm premium normalization, withdrawal-adjusted CAGR, and drawdown assumptions with Annie; these calculations are intentionally unchanged here.
6. Improve large log navigation, chart sizing on narrow screens, and keyboard-accessible data summaries.
7. Consider a shared-element detail transition only when an actual expanded analysis view exists. Simulation wave wipes were subsequently requested explicitly and implemented (see below); ordinary chart-tab changes still use the simpler transition.
8. Add persistent display preferences only with a clear storage contract; current preferences are session-only and do not alter existing user storage.

## Research

- [Scheduler](https://github.com/kg-sato/Scheduler): source and design notes informed the visual vocabulary; expressive ornament is intentionally reduced.
- [Material UI theming](https://mui.com/material-ui/customization/theming/): one `createTheme` foundation with component overrides. Implementation uses the repository's installed MUI 5 API, not a framework migration.
- [web.dev animation guide](https://web.dev/articles/animations-guide): brief transform/opacity motion rather than layout-driven animation; no continuous blur animation.
- [W3C animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html): respect system reduced motion and provide a manual override.
- Apple's Materials page was attempted but returned a JavaScript-only shell; no claims are based on inspecting that page.

## Verification scope

Run the existing percentage/help regression tests plus new workspace tests and a production build. Browser checks cover desktop and narrow layouts, advanced disclosure, help dismissal, and preference controls. A build is not backend validation. Do not commit, push, deploy, or change permissions during this pass.

Verified locally: 42 tests passed across two suites; production build compiled successfully. Desktop and narrow browser checks showed no document-width overflow; disclosure and preferences were exercised. Successful result-context behavior was tested with a clearly test-only fixture. The real backtest service returned a network error, so populated production charts, broker/DB integration, and live API output remain unverified. Existing CRA/webpack and outdated Browserslist-data warnings were not addressed by installing or upgrading dependencies.

## Follow-up: Glass mode and simulation wave

At the user's explicit request, added an optional Glass mode: a static grayscale SVG wave behind glass navigation, scenario settings, and context surfaces. Financial charts and results retain opaque surfaces. Glass and solid-surface preferences are mutually exclusive; system reduced-transparency/high-contrast settings override the glass material.

Every simulation invocation (manual runs, strategy-triggered runs, and retries) starts a 720ms diagonal wipe, independent of whether the API later succeeds. The API starts immediately and the effect does not represent calculation progress or market movement. A new run replaces the old effect. CSS handles the sweep and native SVG animation morphs the internal contours once; no animation dependency or continuous JavaScript loop was added. Escape, hidden-tab changes, manual/system reduced motion, animation completion, and a bounded cleanup fallback remove/suppress the layer. It is noninteractive and hidden from assistive technology.

References: [MDN SVG animate](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/animate) for native finite attribute animation; [MDN matchMedia](https://developer.mozilla.org/en-US/docs/Web/API/Window/matchMedia) for live system preference detection. The original first-pass verification above predates this follow-up; follow-up validation includes transition cleanup/replay, reduced motion, and Glass-mode tests.

Follow-up verification: 49 tests passed across three suites; production build succeeded. Browser inspection confirmed Glass mode, the simulation wipe appearing with `pointer-events: none`, and removal of the layer afterward. No document-width overflow was observed at the desktop breakpoint. Real backend results remain unavailable. The installed test tooling emits an existing React `act` deprecation warning; no dependency upgrades were made.

## Follow-up: monochrome, floating navigation, and chart preview

The user requested an entirely black/white theme, overriding the earlier blue/teal and semantic-color direction. All application palette and wave-art colors are now neutral grays. Status icons and explicit labels retain meaning without color. Strategy events use distinct circle/diamond/triangle markers; strategy and benchmark use solid white versus dashed gray lines.

Removed the full-height sidebar surface, blur, and divider in every appearance mode. Navigation is a narrower transparent rail with compact strategy names. Full descriptions remain available in a native, initially collapsed Strategy guide. Appearance controls can also be collapsed.

Scheduler's bounded transform/opacity motion and `cubic-bezier(.22, 1, .36, 1)` easing inform 260ms directional chart-panel entrances and a sliding tab indicator. Switching strategies reveals the configuration panel with a small vertical offset. These affect surfaces, never interpolate market values, and respect system/manual reduced motion. Rapid tab switches unmount the previous panel without queues or timers.

The frontend targets `http://127.0.0.1:8080/api`, and no local listener was found on port 8080. The API was not started, databases were not initialized, and real results were not fabricated. An explicit Show sample chart action opens an isolated, fixed fictional 2024 dataset with performance/margin/cash tabs and prominent sample labels. It never changes config, enters result processing, creates backtest statistics, or calls the API; a successful real run closes it.

The same new PerformanceChart component styles real results and sample performance: opaque canvas, quiet horizontal grid, sparse date ticks, compact currency axes, end values, solid/dashed legend, and accessible values table loaded only on expansion. It keeps linear, nonanimated data series. Existing backtest math and unit conversions remain unchanged.

Primary references: [Recharts Line API](https://recharts.github.io/en-US/api/Line/) for line/dash/marker options (implemented against installed Recharts 2.15, not newer-only APIs); [W3C Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) for retaining shape/text distinctions in a monochrome interface.

Verification: 51 regression/UI tests passed, including sample/API isolation and forward/reverse tab direction; production build succeeded. Browser inspection showed populated sample charts and their tooltip; real backend-driven chart data remains unverified. jsdom has no actual layout, so Recharts zero-dimension warnings in state tests are not visual validation.

## Follow-up: chart colors, default glass, and testing placement

The surrounding interface remains monochrome, but chart series now use a centralized, distinguishable palette: blue strategy/premium, amber benchmark/interest, lavender margin, and teal cash. Solid versus dashed comparison lines and explicit labels remain, so color is not the only distinction.

Glass is now the default material. Appearance exposes only Solid surfaces and Reduce motion; selecting Solid surfaces removes the wave backdrop and glass treatment. Existing system transparency, contrast, and motion fallbacks remain.

The simulation wipe now starts only on an explicit Run simulation action or explicit retry. Initial loading and strategy navigation do not launch it. Strategy and chart-tab navigation cancel an outstanding wipe; tabs retain the bounded directional slide/fade and sliding indicator. These changes do not alter the simulation payload or financial formulas.

Sample charts are now the final section of the analysis workspace, labeled Testing feature only and Fictional data. They remain isolated from actual results and the API, and can also be opened below populated results.

Verification: 52 tests passed across three suites; the production build succeeded and git diff --check passed. Browser checks confirmed the blue solid/amber dashed performance lines, bottom testing labels, default glass and optional solid checkbox, and directional sample-tab panels without a wave. Real backend-driven results remain unverified because the local API is unavailable. No commits, pushes, deployments, dependency upgrades, or permission changes were made.

## Follow-up: animated scenes, light mode, and sharper geometry

Inspected Scheduler's local `bindLiquidBackground` implementation and scene-specific CSS. Adapted its normalized, scroll-linked parallax to a bounded 64px displacement and added a quiet 24-second CSS transform drift. Each analysis tab selects one of six distinct monochrome contours; sample performance/margin/cash use the corresponding scenes. Scene entrances use a short fade rather than a wipe. The full-screen simulation transition remains restricted to explicit runs/retries, and data series remain nonanimated.

Scroll events schedule at most one pending animation frame, not a continuous JavaScript loop. Hidden-tab changes pause ambient CSS movement and cancel pending frames; manual/system reduced motion removes movement. Unmounting solid-surface artwork cleans up listeners and pending frames.

Appearance now includes a session-only Light mode checkbox. A memoized MUI theme updates controls, menus, alerts, and dates without remounting the dashboard or changing scenario values. Shared CSS tokens cover glass, artwork, chart axes, tables, and tooltips; the light chart palette uses deeper blue/amber/lavender/teal. Selected navigation labels and event markers retain contrast. No new storage contract or dependency was added.

Most surfaces now use 3px corners, inputs/badges use 2px, and navigation uses 3px. Glass remains the default in both themes; Solid surfaces remains optional. Reference: [MUI dark mode](https://mui.com/material-ui/customization/dark-mode/), using the installed MUI 5 palette/ThemeProvider APIs rather than migrating to newer color-scheme APIs.

Verification: 56 tests passed across three suites, covering light-mode parameter preservation/API isolation, distinct tab scenes, hidden-tab/manual motion pause, bounded scroll displacement, and cleanup. Production build succeeded. Computer-use browser checks confirmed both themes, readable light chart colors, scroll displacement, scene selection, reduced-motion behavior, and no document-width overflow at a 600px viewport. Backend-driven results remain unavailable and unverified. No commits, pushes, deployments, permissions changes, or dependency upgrades.

## Follow-up: seven-column research layout and coordinated wave navigation

At the user's request, superseded the simulation-only wipe restriction: changing strategies or chart tabs now replaces the same 720ms decorative wave, while initial loading stays still. Existing title, configuration, and result/preview surfaces share one timing/easing sequence under the wipe. A hook animates existing DOM nodes without remounting inputs, changing chart dimensions, or interpolating recorded data. Interrupted navigation, Escape, hidden tabs, reduced motion, and unmount cancel surface animations; the existing wipe cleanup remains.

The parameter grid uses exactly seven columns at viewport widths of 1800px and above, with 12px gutters and 28px desktop help controls (larger on touch devices). Smaller displays use an adaptive 220px minimum grid, then one column on phones. Content can expand to 2400px instead of the former 1680px cap. Shortened only the two VIX display labels to avoid truncation; normalized units, explanations, conversion scales, and simulation values remain unchanged.

Date fields retain native calendar controls with bounded sizing. All chart date axes now use collision-aware start/end-preserving ticks, concise year/month labels, and dedicated axis height instead of crowded diagonal dates. Currency axes reserve more room and use compact thousands labels. Only tick presentation changed; no data points were removed or formulas changed.

Background artwork now has five layered charcoal/slate/silver strata. Each uses the same compatible SVG command structure and morphs from the preceding tab's contour to the destination with finite native SVG animation. Light-mode artwork and the wipe use corresponding pale-gray tokens rather than a dark overlay. Financial canvases remain opaque. References: [Recharts XAxis](https://recharts.github.io/en-US/api/XAxis/) and [MDN calcMode](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/calcMode).

Verification: 59 tests passed across four suites, including shared surface timing, input-node preservation, interrupted navigation cancellation, and five synchronized contour morphs. Production build succeeded. At 1920px, browser measurements confirmed seven fields in the first advanced row and date inputs with equal scroll/client widths (no horizontal clipping). Browser inspection confirmed the three visible surfaces had identical animated opacity/transform values while the wipe and five contour morphs were active. Real backend results remain unavailable; production chart data is not visually verified. No commit, push, deployment, new dependency, or permission changes.

## Clarification: individual information-surface motion

The annotated screenshot clarified that the user meant distinct motion for the context strip, status notice, and configuration panel, not one animation of the entire destination workspace. Replaced shared navigation timing with separate restrained entrances: context slides from the left (320ms), status drops/fades (240ms), configuration rises (420ms), and results slide/fade from the right (360ms). The main heading and tab controls are not entrance-animation targets. Async loading/error notices also animate when they mount. Input DOM nodes, focus, seven-column layout, dates, and chart coordinates remain unchanged.

Restored the full-screen wave to explicit simulation runs/retries only. Strategy/chart navigation cancels an outstanding wipe and uses the individual surface motion; background strata still morph alongside scene changes. Existing Escape, hidden-tab, reduced-motion, interruption, and unmount cleanup remain. Verification updated the regression tests to enforce distinct transforms/durations and absence of navigation wipes; no commits or pushes.
