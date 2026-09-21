# Fund Lens Visual System

## Product Direction

Fund Lens is a calm research workbench for reviewing fund-blogger activity, not a promotional trading dashboard. The interface should make comparison, review, and audit trails easy to scan while keeping attention on the data.

## Visual Language

- Canvas: warm off-white `#f4f6fa` with white content surfaces.
- Navigation: deep navy `#10263f`; active navigation uses a restrained mint accent.
- Type: system sans for controls and dense data; a restrained serif for page titles and primary metrics.
- Surfaces: thin cool-gray borders, small radii, and low-contrast shadows. Avoid floating-card excess.
- Accent: muted blue for links and chart structure; amber only for warnings and duplicate-review cues.
- Density: compact enough for a research table, with clear section headings and generous page-level breathing room.

## Market Semantics

The product follows mainland China A-share display convention:

- Positive return, gain, and upward movement are red.
- Negative return, loss, and downward movement are green.
- Zero and unavailable values are muted rather than directional.
- Maximum drawdown remains a negative metric semantically; it is rendered green when the numeric value is negative because it is a decline, and muted when unavailable.
- Currency is RMB with two decimal places. Percentages and drawdown values use two decimal places.
- Values unavailable during the first 30 observation days display `--`; the status remains `观察期中`.

## Layout Contract

- `.app-shell` owns the viewport with `min-height: 100dvh`.
- `.main-frame` is the flexible column and must retain `min-width: 0`.
- `.content-area` is the only primary page scroll container; the shell and frame must not create competing horizontal scrollbars.
- Grids use `minmax(0, 1fr)` so tables and charts can shrink within the frame.
- At narrow widths, page padding and grid columns collapse before content is clipped. Tables may scroll horizontally inside their own Element Plus table wrapper.

## Component States

- Loading: preserve the page structure and use the existing Element Plus skeleton/loading states.
- Empty: explain what is missing and provide the next relevant action where one exists.
- Error: state the failed operation and provide a route back to a stable page.
- Disabled: retain readable contrast and communicate why an OCR row cannot be edited.
- Active/selected: use the navy navigation surface and mint edge, not saturated fills.

## Shared Tokens

The source of truth is `src/styles.css`. Keep token names stable when possible:

- `--ink`, `--muted`, `--line`, `--surface`, `--canvas`, `--navy`
- `--green` for negative/downward market values
- `--red` for positive/upward market values
- `--amber` for warnings and review attention

New components should consume these tokens rather than introducing page-local colors. Chart palettes should remain muted and legible against white surfaces.
