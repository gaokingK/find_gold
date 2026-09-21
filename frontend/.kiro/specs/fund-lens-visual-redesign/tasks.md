# Implementation Plan: Fund Lens Visual Redesign

## Overview

Implement the Fund Lens visual redesign as a presentation-layer migration over the existing Vue 3, Vue Router, Element Plus, and ECharts application. Establish the shared visual foundation first, then migrate the Shell and reusable components before migrating the Overview, History, Import/OCR, Blogger Detail, and Settings views. Preserve all existing routes, service calls, domain fields, filters, validation rules, CRUD behavior, OCR review behavior, chart data, and confirmation semantics.

The design explicitly determines that property-based testing is not applicable to this UI visual redesign. Do not add a property-testing dependency or property-based test tasks; use the existing Vitest/Vue Test Utils examples, interaction tests, build checks, and browser-based visual/accessibility QA described below.

## Tasks

- [ ] 1. Establish the shared visual foundation
  - [ ] 1.1 Update `src/styles.css` with the compatible color roles and visual tokens from the design: existing `--ink`, `--muted`, `--line`, `--surface`, `--canvas`, `--navy`, `--green`, `--red`, and `--amber`, plus spacing, typography, radius, shadow, focus, blue, and on-navy tokens.
    - Add the 4px spacing scale, limited radius levels, card and overlay shadows, visible focus ring, reduced-motion handling, and the desktop/intermediate/mobile breakpoint rules.
    - Add centralized Element Plus overrides and shared layout contracts for cards, feedback, tables, dialogs, and state styling; do not add page-specific business colors or change A-share tone semantics.
    - Preserve the existing `valueTone`/formatter behavior: positive values remain red, negative values green, and zero/null values muted with existing `--` and “观察期中” semantics.
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 8.1, 9.1, 9.5, 10.4, 10.5, 11.1, 11.4_

  - [ ] 1.2 Add pure presentation-layer types and adapters for visual tones, async states, page feedback, and navigation metadata without changing `src/services/` contracts or domain models.
    - Keep business states such as blogger status and OCR review actions unchanged; adapters may only prepare display props, labels, icons, and feedback text.
    - Include route-to-page-title/path metadata and `/bloggers/:id` to overview active-state mapping as pure, testable helpers.
    - _Requirements: 2.2, 2.3, 9.4, 10.6, 11.2, 11.3, 11.4_

  - [ ] 1.3 Create the ECharts visual theme/configuration adapter used by Blogger Detail.
    - Consume CSS/visual tokens for chart text, grid lines, low-saturation series colors, backgrounds, and tooltip contrast; do not use A-share semantic colors for chart structure.
    - Keep chart data and business calculations in `BloggerDetailView.vue`, and expose only presentation configuration plus resize-safe helpers.
    - _Requirements: 1.1, 1.3, 6.2, 6.5, 11.1, 11.3_

- [ ] 2. Implement Shell, navigation, and shared presentation components
  - [ ] 2.1 Implement or organize the shared `PageHeader`, `SurfaceCard`, `FilterBar`, `TableFrame`, `StatusTag`, `FeedbackRegion`, and `ResponsiveDialog` components under `src/components/`.
    - Give each component stable slots/props matching the design, preserve minimum heights for loading and feedback regions, and make status meaning available through text plus icon/shape/border rather than color alone.
    - Support loading, empty, error, disabled, selected, hover, pressed, keyboard-focus, and reduced-motion states using the shared tokens.
    - Keep `MetricCard`, `EmptyState`, `BloggerStatusTag`, and the three domain table components compatible with their current business-facing props and events while adopting the shared visual contracts.
    - _Requirements: 1.2, 1.3, 1.4, 9.1, 9.2, 9.3, 9.4, 10.1, 10.4, 10.5, 11.1, 11.4_

  - [ ] 2.2 Refactor `src/components/AppShell.vue` and `src/layouts/AppLayout.vue` to use the shared Shell presentation structure.
    - Preserve the four navigation items, existing `router.push` behavior, the demo-mode status, brand text/subtitle, page title/path mapping, and the main content scroll ownership.
    - Map `/bloggers/:id` to the Overview navigation selected state while keeping the detail page return-to-overview entry.
    - Use real button/link semantics, `aria-current`, accessible names for icon-only mobile navigation, visible focus styles, and a stable feedback region without reading business data in the Shell.
    - Enforce `min-width: 0`, `min-height: 100dvh`, and one primary content scroll container so Shell and table scrolling do not compete.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.1, 8.2, 8.4, 9.5, 10.1, 10.2, 10.4, 10.6, 11.1, 11.2_

  - [ ] 2.3 Update `src/components/PositionTable.vue`, `src/components/OperationTable.vue`, `src/components/OcrReviewTable.vue`, `src/components/MetricCard.vue`, `src/components/EmptyState.vue`, and `src/components/BloggerStatusTag.vue` to consume shared table, metric, empty, and status styling.
    - Preserve all current columns, fields, sorting, formatter/valueTone output, action events, domain labels, disabled rules, and empty/loading behavior.
    - Ensure table overflow is owned by the table wrapper, table regions have an accessible label or helper text, and status labels remain understandable without color.
    - _Requirements: 1.5, 3.6, 4.3, 5.2, 5.3, 5.4, 5.6, 6.2, 7.2, 8.4, 8.5, 9.1, 10.1, 10.5, 10.6, 11.3, 11.4_

- [ ] 3. Migrate the Overview page
  - [ ] 3.1 Refactor `src/views/OverviewView.vue` into the designed PageHeader, four-metric grid, FilterBar, and TableFrame composition.
    - Preserve the “追踪池概览” title/description, import entry, four existing metrics, filter fields, result ordering, `service.listBloggers()`/sector loading, loading placeholder structure, empty-state actions, and `router.push('/bloggers/:id')` detail navigation.
    - Use responsive grid rules so wide screens establish metric/list hierarchy, intermediate screens wrap filters, mobile screens become single-column, and only the blogger table scrolls horizontally.
    - Do not change service data, filtering semantics, or business calculations.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 8.1, 8.3, 8.4, 8.7, 9.2, 9.5, 11.2, 11.3_

  - [ ]* 3.2 Add Vue Test Utils/Vitest example tests for Overview navigation, filter submission/clearing, loading structure, empty-state actions, metric tone rendering, and detail-route navigation using mocked services.
    - Assert existing service parameters and route targets without reimplementing filtering or service logic.
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 10.2, 11.3_

- [ ] 4. Migrate the History page and detail drawer
  - [ ] 4.1 Refactor `src/views/HistoryView.vue` to use PageHeader, FilterBar, TableFrame, FeedbackRegion, and ResponsiveDialog/drawer presentation.
    - Preserve date filtering, query behavior, new-import navigation, batch fields, recognition/review status semantics, `selected`, `drawerVisible`, `openDetail()`, raw OCR text, structured records, and all existing list operations.
    - Implement the designed scroll/query/list state snapshot and close behavior: restore the complete state only when background scroll restoration succeeds; otherwise restore none of the grouped state.
    - Give the drawer title, close control, raw-text region, and structured table accessible names; constrain narrow-screen width to the available viewport and scroll inside the panel.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.4, 8.6, 9.5, 10.1, 10.2, 10.6, 11.3_

  - [ ]* 4.2 Add component tests for history filtering, empty fallback/new-import action, drawer open/close behavior, grouped state restoration success, and all-or-nothing fallback when scroll restoration fails.
    - Verify mocked service calls and preserve the existing batch/query/list values through the tested transitions.
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6, 10.2, 11.3_

- [ ] 5. Migrate the screenshot Import and OCR Review page
  - [ ] 5.1 Refactor `src/views/ImportView.vue` into the designed upload card, OCR result card, fixed file-state rows, review table, and stable feedback regions.
    - Preserve operation-date selection, PNG/JPG/JPEG selection or drag/drop, size and format validation, multi-file status, `service.recognizeScreenshot(file, operationDate)`, OCR record editing, accept/reject actions, duplicate detection, and `confirmOcrRecords()` behavior.
    - Display pending, recognized, and failed file states with fixed space, progress/status text, and local error explanations; express pending and suspected-duplicate risks with text plus non-color cues.
    - Keep the confirmation dialog and cancellation semantics unchanged: cancelling with pending records must not mutate `records`; success/failure feedback must remain visible without hiding final accepted/rejected/pending distinctions.
    - Keep field errors beside date/file/amount controls and retain all existing disabled and submission-blocking rules.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 8.3, 8.6, 8.7, 9.2, 9.4, 10.1, 10.2, 10.5, 11.3_

  - [ ]* 5.2 Add component tests for file validation, date validation, recognition success/failure rows, OCR amount editing, accept/reject, duplicate and pending indicators, confirmation/cancellation, and success/error feedback.
    - Assert service calls and UI state transitions while leaving domain and service rules in their existing implementations.
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 10.2, 11.3_

- [ ] 6. Migrate the Blogger Detail page and charts
  - [ ] 6.1 Refactor `src/views/BloggerDetailView.vue` into the designed return/header, four metrics, chart grid, positions card, and operations card.
    - Preserve `/bloggers/:id`, `getBloggerDetail(id)`, return-to-overview behavior, blogger identity/sector/date/status, import entry, all four metric fields and formatting, positions, operations, and monthly/holding chart data.
    - Implement skeleton content matching the final metric/chart/table structure, stable error feedback with a return action, and a usable Shell when detail loading fails.
    - Use the chart theme adapter, `min-width: 0`, stable chart heights, `ResizeObserver` or equivalent lifecycle resize handling, readable title/legend/tooltip placement, and `dispose` on unmount.
    - _Requirements: 1.5, 6.1, 6.2, 6.3, 6.4, 6.5, 8.3, 8.7, 9.2, 9.5, 10.2, 11.2, 11.3_

  - [ ]* 6.2 Add component tests for detail loading/error/return states, metric tone/null formatting, chart initialization and resize/dispose lifecycle, and table composition with mocked detail data.
    - Keep chart assertions focused on configuration/lifecycle and do not alter or duplicate detail business calculations.
    - _Requirements: 1.5, 6.1, 6.3, 6.4, 6.5, 10.2, 11.3_

- [ ] 7. Migrate the Settings page
  - [ ] 7.1 Refactor `src/views/SettingsView.vue` into the shared PageHeader, SurfaceCard, tabs, TableFrame, ResponsiveDialog, and delete-confirmation presentation.
    - Preserve blogger, fund, and initial-position tabs; create/edit/delete/save service calls; field labels and rules; current tab selection; list state; and existing data model fields.
    - Distinguish primary, secondary/edit, and dangerous/delete actions; show type-specific dialog titles, labels, validation messages, cancel/save controls, and accessible names.
    - Require delete confirmation before calling the delete service; cancellation leaves the object and tab unchanged. Save errors keep the form open and preserve the current tab; success/error feedback uses the shared fixed region.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.3, 8.6, 8.7, 9.1, 9.4, 10.1, 10.2, 11.3_

  - [ ]* 7.2 Add component tests for all three tabs, create/edit dialog variants, field validation, save success/failure, delete confirmation/cancellation, and current-tab/list preservation.
    - Assert mocked CRUD call parameters and cancellation behavior without changing service rules.
    - _Requirements: 7.1, 7.3, 7.4, 7.5, 7.6, 10.2, 11.3_

- [ ] 8. Complete cross-page responsive, state, and accessibility integration
  - [ ] 8.1 Integrate and verify the three responsive layout contracts across Shell, all five view areas, and shared components at `<=720px`, `721–1199px`, and `>=1200px`.
    - At mobile widths use icon navigation with accessible labels, one-column page flow, 16px content padding, wrapping status labels, and usable full-width actions; at intermediate widths shrink padding and reflow metrics, charts, import areas, filters, and forms; at wide widths use the intended sidebar and multi-column hierarchy.
    - Ensure tables own horizontal scrolling, no competing Shell/page overflow exists above 320px, 320px remains usable even when page and table scrolling coexist, and dialogs/drawers scroll internally without covering headings or primary actions.
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 9.5, 11.5_

  - [ ] 8.2 Complete cross-page accessibility and interaction-state hardening.
    - Audit navigation, headings, sections, buttons, links, filters, tabs, table actions, drawers, dialogs, status feedback, and scroll regions for semantic elements and accessible names.
    - Ensure keyboard paths cover navigation, primary actions, filtering, import/review, details, confirmations, and return-to-overview; focus rings are visible and non-color-only, dialog focus enters and returns correctly, Escape/close controls work, and unavailable navigation does not block other keyboard tasks.
    - Ensure WCAG 2.1 AA contrast targets, text/icon/shape status cues, `role="status"`/`role="alert"` feedback, heading order, and `prefers-reduced-motion` behavior are consistent across all views.
    - _Requirements: 9.1, 9.3, 9.4, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.1, 11.4, 11.5_

- [ ] 9. Run automated regression and interaction checks
  - [ ]* 9.1 Add or update pure adapter and shared-component Vitest examples for route/title mapping, blogger-detail active navigation, value-tone mapping, status labels, and empty/error feedback text.
    - Keep tests example-based; do not introduce a property-based testing package or Correctness Properties/PBT tasks because the design explicitly excludes them.
    - _Requirements: 2.2, 2.3, 1.5, 9.4, 11.4_

  - [ ]* 9.2 Run and maintain the existing unit suite plus the new high-risk component tests for Shell active/aria state, Overview filtering, History drawer restoration, Import/OCR confirmation, Settings delete cancellation, and Detail loading/error behavior.
    - Use mocked services and assert calls, parameters, route targets, and visible states; do not reimplement service rules in tests.
    - _Requirements: 2.4, 3.2, 4.5, 4.6, 5.5, 7.4, 7.5, 10.2, 11.3_

- [ ] 10. Validate build and perform visual/accessibility QA
  - [ ]* 10.1 Run `npm.cmd run test:unit` and `npm.cmd run build`; if the repository’s Vue tooling exposes a separate type-check command, run the corresponding `vue-tsc` check and fix template, TypeScript, ECharts, or Element Plus integration errors.
    - Confirm all existing formatter, import-flow, mock-service, overview contract, and settings tests remain green and no source route/service contract was changed.
    - _Requirements: 11.2, 11.3, 11.5_

  - [ ]* 10.2 Perform browser-based visual and responsive QA using the existing screenshot workflow for `/`, `/bloggers/:id`, `/import`, `/history`, and `/settings` at 1440px, 1024px, and 320px widths.
    - Record route- and viewport-named screenshots using the existing QA assets/conventions; check no Shell overflow, no card/button overlap, reachable table columns, visible headings/actions, stable loading/empty/error/disabled/focus states, and consistent tokens, whitespace, typography, card boundaries, and restrained shadows.
    - Specifically check Detail chart resize/title/legend/tooltip containment, History drawer open/close and state restoration, Import file/OCR pending/duplicate feedback, and Settings tabs/dialog/delete confirmation.
    - _Requirements: 3.6, 4.2, 4.5, 5.2, 5.4, 5.5, 6.5, 7.1, 8.1, 8.4, 8.5, 8.6, 8.7, 9.2, 9.5, 10.4, 10.5, 11.5_

  - [ ]* 10.3 Complete a keyboard and semantic accessibility pass at desktop and 320px widths, including focus visibility/order, accessible names, heading/region hierarchy, table scroll instructions, dialog focus return, status announcements, and reduced-motion behavior.
    - _Requirements: 9.1, 9.3, 9.4, 10.1, 10.2, 10.4, 10.5, 10.6, 11.5_

- [ ] 11. Final checkpoint - Ensure all automated checks and visual requirements pass
  - Ensure all tests pass, the production build succeeds, all five view areas plus Blogger Detail retain their routes and business behavior, and the 1440px/1024px/320px visual and accessibility checks are complete. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test or validation tasks and may be skipped for a faster MVP; core implementation tasks are unstarred.
- No property-based testing task or dependency is included because the design’s Testing Strategy explicitly states that PBT is not applicable to this UI visual redesign.
- Existing business behavior is the source of truth: do not change services, domain fields, route paths, formatter semantics, OCR rules, confirmation rules, CRUD behavior, or chart data calculations.
- Shared components must consume the visual tokens and remain presentation-only; page views continue to own service calls, business state, and domain transformations.
- Visual QA should compare against the existing `fund2-qa-*.png` and `fund2-qa-final-*.png` assets for regression context, not attempt pixel-for-pixel reproduction of reference imagery.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3"] },
    { "id": 4, "tasks": ["3.1", "4.1", "5.1", "6.1", "7.1"] },
    { "id": 5, "tasks": ["3.2", "4.2", "5.2", "6.2", "7.2"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2"] },
    { "id": 8, "tasks": ["9.1", "9.2"] },
    { "id": 9, "tasks": ["10.1"] },
    { "id": 10, "tasks": ["10.2", "10.3"] }
  ]
}
```
