# Mini ChatChat Component Library v1

This document defines reusable component contracts for the next React refactor. It is grounded in the current Mini ChatChat React implementation, backend APIs, Design Bible, Design Tokens, Page Wireframes, UI Pattern Library, and the component library reference image.

This document does not create components or prescribe page layout. It defines when each component is used, what data it accepts, how it behaves, and how it should be tested.

## 1. Component Contract Template

Every component entry in this library uses the same contract.

### Purpose

What the component exists to do.

### When to use

The product situations where this component is appropriate.

### When not to use

The situations where the component would create noise, duplicate behavior, or imply unsupported functionality.

### Anatomy

Named internal parts. These are semantic parts, not required DOM structure.

### Variants

Allowed variants. If there are no variants, write `Not applicable`.

### Sizes

Allowed sizes. If fixed or not size-driven, write `Not applicable`.

### States

Supported UI states such as default, hover, focused, selected, active, disabled, loading, error, empty, success, warning, danger.

### Props / data contract

Expected React props or data shape. This is a contract, not implementation code.

### Token usage

Which design tokens should be used.

### Keyboard behavior

Required keyboard behavior. If non-interactive, write `Not applicable`.

### Accessibility

ARIA, semantic HTML, focus, labels, and screen reader requirements.

### Responsive behavior

How the component behaves across desktop, tablet, and mobile.

### Loading behavior

How the component shows loading. If no loading state, write `Not applicable`.

### Error behavior

How the component shows errors. If no error state, write `Not applicable`.

### Testing requirements

What automated or manual UI tests must verify.

### Do

Correct usage rules.

### Don't

Incorrect usage rules.

## 2. Foundation Components

### `Text`

#### Purpose

Render readable product text with consistent typography and color.

#### When to use

Use for body copy, captions, labels, hints, metadata, and source previews.

#### When not to use

Do not use for page titles, section titles, status badges, code blocks, buttons, or icon-only labels.

#### Anatomy

- Text node.
- Optional semantic element.
- Optional tone.

#### Variants

- `body`
- `bodySmall`
- `caption`
- `label`
- `muted`
- `danger`
- `success`
- `warning`
- `info`

#### Sizes

Uses typography variants only. Do not add arbitrary size props.

#### States

- Default.
- Muted.
- Disabled.
- Semantic tone.

#### Props / data contract

- `as`: semantic element, default `p` or `span`.
- `variant`.
- `tone`.
- `children`.
- `truncate`: optional boolean.

#### Token usage

- `font-family-sans`
- `font-size-body`
- `font-size-body-small`
- `font-size-label`
- `font-size-caption`
- `line-height-body`
- `line-height-compact`
- text color tokens.

#### Keyboard behavior

Not applicable.

#### Accessibility

Use semantic elements. Do not use color alone to communicate critical state.

#### Responsive behavior

Text wraps by default. Long metadata truncates only when the full value is accessible through title, detail panel, or expanded view.

#### Loading behavior

Not applicable.

#### Error behavior

Use semantic tone only for supporting text. Use `InlineError` for actual errors.

#### Testing requirements

Verify text renders with the requested semantic element and does not overflow narrow containers.

#### Do

- Use strict variants.
- Use muted text for metadata.

#### Don't

- Create one-off font sizes.
- Use `Text` to fake a button.

### `Heading`

#### Purpose

Render page, section, and panel headings with consistent hierarchy.

#### When to use

Use for page titles, section headings, panel titles, dialog titles, and card titles.

#### When not to use

Do not use for labels, badges, source metadata, row actions, or chat answer paragraphs.

#### Anatomy

- Heading text.
- Optional eyebrow above it.
- Optional description below it.

#### Variants

- `display`
- `page`
- `section`
- `panel`
- `card`

#### Sizes

Fixed by variant.

#### States

Default only.

#### Props / data contract

- `level`: `1 | 2 | 3 | 4`.
- `variant`.
- `eyebrow`: optional.
- `description`: optional.
- `children`.

#### Token usage

- `font-size-display`
- `font-size-heading`
- `font-size-title`
- `font-weight-bold`
- `font-weight-semibold`
- `line-height-display`
- `line-height-heading`
- text tokens.

#### Keyboard behavior

Not applicable.

#### Accessibility

Heading levels must follow document hierarchy. Do not skip levels for styling.

#### Responsive behavior

Page headings may reduce to title scale on mobile. Do not use viewport-based fluid type unless tokenized.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify heading level and accessible name.

#### Do

- Use one page H1 per workspace.
- Use panel headings quietly.

#### Don't

- Make every section visually equal to the page title.
- Use heading styles on non-heading elements.

### `Icon`

#### Purpose

Show familiar visual symbols that support labels and controls.

#### When to use

Use in navigation, tool status, file rows, source references, buttons, and empty states.

#### When not to use

Do not use decorative icons that add no meaning. Do not replace text with an unfamiliar icon without an accessible label.

#### Anatomy

- Icon glyph.
- Optional accessible label when icon-only.

#### Variants

- `nav`
- `status`
- `action`
- `file`
- `tool`

#### Sizes

- `sm`
- `md`
- `lg`

#### States

- Default.
- Muted.
- Active.
- Danger.
- Disabled.

#### Props / data contract

- `name`.
- `size`.
- `tone`.
- `ariaLabel`: required when icon is interactive or icon-only.
- `decorative`: boolean.

#### Token usage

- `icon-size-sm`
- `icon-size-md`
- `icon-size-lg`
- semantic color tokens.

#### Keyboard behavior

Not applicable unless wrapped by a button or link.

#### Accessibility

Decorative icons use `aria-hidden=true`. Meaningful icon-only controls need `aria-label`.

#### Responsive behavior

Use the same size tokens. Avoid shrinking icons below `icon-size-sm`.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify icon-only controls expose an accessible label.

#### Do

- Pair unfamiliar icons with visible text.
- Keep icons aligned with text.

#### Don't

- Use icon color as the only status cue.
- Invent custom SVGs when a standard icon exists.

### `Divider`

#### Purpose

Separate related sections without adding visual weight.

#### When to use

Use between sidebar sections, panel sections, list groups, and dialog body/action areas.

#### When not to use

Do not use when spacing alone can clarify separation. Do not use inside every card row.

#### Anatomy

- Line.
- Optional label only for section grouping.

#### Variants

- `subtle`
- `default`
- `strong`

#### Sizes

Not applicable.

#### States

Default only.

#### Props / data contract

- `orientation`: `horizontal | vertical`.
- `variant`.
- `label`: optional.

#### Token usage

- `border-width-default`
- `color-border-subtle`
- `color-border-default`
- `color-border-strong`
- spacing tokens for margins.

#### Keyboard behavior

Not applicable.

#### Accessibility

Use `role=separator` only when the divider has semantic meaning.

#### Responsive behavior

Vertical dividers collapse to horizontal or disappear on mobile.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify no divider causes overflow in compact layouts.

#### Do

- Use subtle dividers.

#### Don't

- Build heavy grid borders everywhere.

### `Surface`

#### Purpose

Provide semantic surface levels for panels, cards, composer, popovers, and dialogs.

#### When to use

Use when content needs a meaningful background or elevation level.

#### When not to use

Do not wrap every group in a surface. Do not nest surfaces without a clear hierarchy.

#### Anatomy

- Container.
- Optional header.
- Optional body.
- Optional footer.

#### Variants

- `base`
- `subtle`
- `elevated`
- `critical`

#### Sizes

Not applicable.

#### States

- Default.
- Hover when selectable.
- Selected when representing a selected object.
- Error for critical surface.

#### Props / data contract

- `variant`.
- `interactive`: boolean.
- `selected`: boolean.
- `as`.
- `children`.

#### Token usage

- background color tokens.
- border tokens.
- radius tokens.
- shadow tokens only for elevation.
- spacing tokens for padding.

#### Keyboard behavior

If interactive, it must be a real button/link or contain a focusable control.

#### Accessibility

Do not make a non-semantic div clickable. Use semantic elements.

#### Responsive behavior

Padding may reduce on mobile using spacing tokens.

#### Loading behavior

Can contain skeleton/loading child components.

#### Error behavior

Critical variant may host `InlineError`; do not use red-tinted surfaces as decoration.

#### Testing requirements

Verify interactive surfaces are keyboard reachable and not nested inside clickable parents.

#### Do

- Use surfaces to clarify importance.

#### Don't

- Create card-inside-card layouts.
- Use shadows as decoration.

### `Stack`

#### Purpose

Arrange children vertically with tokenized spacing.

#### When to use

Use for forms, panel sections, empty states, source lists, and dialog bodies.

#### When not to use

Do not use for two-dimensional grids, tables, or inline controls.

#### Anatomy

- Vertical container.
- Children.

#### Variants

Not applicable.

#### Sizes

- `1`
- `2`
- `3`
- `4`
- `5`
- `6`
- `8`
- `10`
- `12`
- `16`

#### States

Not applicable.

#### Props / data contract

- `gap`.
- `align`.
- `as`.
- `children`.

#### Token usage

- spacing tokens.

#### Keyboard behavior

Not applicable.

#### Accessibility

Preserve child semantics.

#### Responsive behavior

Gap may accept responsive token mapping only when defined.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify no child overlap in mobile width.

#### Do

- Use for predictable vertical rhythm.

#### Don't

- Hardcode pixel gaps in component CSS.

### `Inline`

#### Purpose

Arrange children horizontally with tokenized spacing and wrapping behavior.

#### When to use

Use for action rows, metadata rows, badges, source references, and compact controls.

#### When not to use

Do not use for primary page layout or dense tables.

#### Anatomy

- Horizontal container.
- Children.

#### Variants

Not applicable.

#### Sizes

Uses spacing token gap only.

#### States

Not applicable.

#### Props / data contract

- `gap`.
- `align`.
- `justify`.
- `wrap`.
- `children`.

#### Token usage

- spacing tokens.

#### Keyboard behavior

Not applicable.

#### Accessibility

Preserve child focus order.

#### Responsive behavior

Can wrap on mobile. Do not force horizontal overflow for controls.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify wrapping does not hide actions on mobile.

#### Do

- Use for compact metadata and actions.

#### Don't

- Use it to fake a toolbar without semantic actions.

### `VisuallyHidden`

#### Purpose

Provide screen-reader-only text.

#### When to use

Use for icon-only button labels, hidden form labels, and extra status context.

#### When not to use

Do not hide essential visible labels from sighted users when a visible label is needed for clarity.

#### Anatomy

- Hidden text node.

#### Variants

Not applicable.

#### Sizes

Not applicable.

#### States

Not applicable.

#### Props / data contract

- `children`.
- `as`: optional semantic element.

#### Token usage

Not applicable.

#### Keyboard behavior

Not applicable.

#### Accessibility

Must use a standard visually-hidden CSS pattern that remains available to screen readers.

#### Responsive behavior

Not applicable.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify accessible names exist for icon-only controls.

#### Do

- Use for screen reader context.

#### Don't

- Use it to hide interactive controls.

## 3. Navigation Components

### `AppShell`

#### Purpose

Provide the stable product shell: Sidebar, TopBar, Workspace, Context Panel mount points, Toast layer, and Dialog layer.

#### When to use

Use once at the app root.

#### When not to use

Do not create nested shells inside pages.

#### Anatomy

- Sidebar area.
- TopBar area.
- Workspace area.
- Optional conversation dock.
- Optional Context Panel slot.
- Toast layer.
- Dialog layer.

#### Variants

- `withConversationDock`
- `fullWidth`
- `compact`

#### Sizes

Uses shell size tokens.

#### States

- Default.
- Mobile navigation open.
- Context panel collapsed.

#### Props / data contract

- `activePage`.
- `sidebar`.
- `topbar`.
- `conversationDock`.
- `contextPanel`.
- `children`.
- `isSidebarOpen`.
- `isContextPanelOpen`.

#### Token usage

- `sidebar-width`
- `sidebar-collapsed-width`
- `context-panel-width`
- `content-max-width`
- z-index tokens.
- spacing tokens.

#### Keyboard behavior

Navigation order must move Sidebar -> TopBar -> Workspace -> Context Panel.

#### Accessibility

Use landmarks: `nav`, `header`, `main`, `aside`. Provide skip-to-main when implemented.

#### Responsive behavior

Desktop shows persistent Sidebar. Tablet may collapse Sidebar. Mobile uses drawer navigation and bottom sheet/detail page for Context Panel.

#### Loading behavior

Shell should not show global loading except for initial app bootstrap.

#### Error behavior

Shell may host page error fallback, but page-specific errors belong in workspace.

#### Testing requirements

Verify landmarks, focus order, mobile drawer, and no unreachable scroll areas.

#### Do

- Keep one shell.

#### Don't

- Add page-specific debug controls to shell.

### `SidebarNavigation`

#### Purpose

Navigate between Chat, Agent, Knowledge, and System.

#### When to use

Use inside Sidebar.

#### When not to use

Do not duplicate workspace navigation in page headers.

#### Anatomy

- Navigation list.
- Navigation item.
- Active indicator.
- Optional icon.

#### Variants

- `expanded`
- `collapsed`

#### Sizes

Not applicable.

#### States

- Default.
- Hover.
- Focus.
- Active.
- Disabled only if a route is genuinely unavailable.

#### Props / data contract

- `activePage`.
- `items`.
- `onSelectPage`.

#### Token usage

- selected and hover background tokens.
- text tokens.
- icon size tokens.
- spacing tokens.

#### Keyboard behavior

Tab reaches each nav item. Enter/Space activates.

#### Accessibility

Use `nav` with label. Mark active item with `aria-current=page`.

#### Responsive behavior

Collapsed mode shows icons with accessible labels. Mobile appears inside drawer.

#### Loading behavior

Not applicable.

#### Error behavior

Not applicable.

#### Testing requirements

Verify active route, keyboard activation, and accessible names.

#### Do

- Keep four primary destinations.

#### Don't

- Add unsupported navigation items.

### `ConversationSidebar`

#### Purpose

Display conversation history, search, New Chat, rename, and delete actions.

#### When to use

Use in Chat and Agent workspaces.

#### When not to use

Do not show on Knowledge or System unless conversation context is relevant.

#### Anatomy

- Header.
- New Chat action.
- Search field.
- Conversation list.
- Row action menu.
- Delete confirmation dialog.

#### Variants

- `dock`
- `drawer`
- `collapsed`

#### Sizes

Uses sidebar/conversation dock width tokens when available.

#### States

- Loading.
- Empty.
- Filtered empty.
- Active conversation.
- Row hover.
- Menu open.
- Delete confirming.

#### Props / data contract

- `conversations`: id, title, create_time, updated_time.
- `currentConversationId`.
- `onNew`.
- `onLoad`.
- `onRename`.
- `onDelete`.
- `isLoading`.

#### Token usage

- spacing tokens.
- selected/hover background tokens.
- text-muted token.
- border tokens.

#### Keyboard behavior

Search is focusable. Conversation rows activate with Enter/Space. Menu opens with Enter/Space and supports Escape close.

#### Accessibility

Use labelled region. Menus need accessible labels. Delete must use confirmation dialog.

#### Responsive behavior

Desktop dock scrolls independently. Mobile appears in drawer.

#### Loading behavior

Use skeleton rows or quiet loading text.

#### Error behavior

Show inline error if conversations cannot load.

#### Testing requirements

Verify New Chat, load, rename, delete, search, active row, persistence after reload.

#### Do

- Sort by backend `updated_time` order.

#### Don't

- Let row menus be hover-only without keyboard access.

### `TopBar`

#### Purpose

Show compact runtime context and global utility controls.

#### When to use

Use in App Shell across all workspaces.

#### When not to use

Do not use it for page-specific primary actions or debug controls.

#### Anatomy

- Runtime summary.
- Current model/provider summary.
- Optional health indicator.
- Utility area.

#### Variants

- `default`
- `compact`

#### Sizes

Uses future `topbar-height` token.

#### States

- Default.
- Degraded status.
- Loading status.

#### Props / data contract

- `provider`.
- `model`.
- `healthStatus`.
- `currentKb`.
- `chatMode`.

#### Token usage

- text tokens.
- status tokens.
- border tokens.
- spacing tokens.

#### Keyboard behavior

Interactive utility controls must be reachable after navigation and before main workspace.

#### Accessibility

Use `header`. Status needs text, not color only.

#### Responsive behavior

Hide secondary metadata on mobile behind details or System page.

#### Loading behavior

Show small skeleton/status placeholder.

#### Error behavior

Show degraded indicator; detailed errors belong in System.

#### Testing requirements

Verify no API key is rendered and compact layout does not overflow.

#### Do

- Keep it factual and quiet.

#### Don't

- Put source cards, retrieval controls, or tool trace in TopBar.

## 4. Input and Action Components

### `Button`

#### Purpose

Trigger actions with a clear hierarchy.

#### When to use

Use for real user actions backed by UI state or backend capability.

#### When not to use

Do not use for fake controls, navigation rows that need `aria-current`, or non-interactive labels.

#### Anatomy

- Label.
- Optional icon.
- Optional loading indicator.

#### Variants

- `primary`
- `secondary`
- `ghost`
- `outline`
- `danger`
- `icon`
- `toolbar`

#### Sizes

- `sm`
- `md`
- `lg`

#### States

- Default.
- Hover.
- Pressed.
- Focus.
- Disabled.
- Loading.
- Success.
- Error.

#### Props / data contract

- `variant`.
- `size`.
- `isLoading`.
- `disabled`.
- `disabledReason`.
- `icon`.
- `children`.
- `onClick`.
- `type`.

#### Token usage

- brand, danger, text, border, hover, focus tokens.
- control height tokens.
- radius tokens.
- motion tokens.

#### Keyboard behavior

Enter/Space activates. Loading or disabled buttons do not activate.

#### Accessibility

Icon-only buttons require `aria-label`. Disabled reason should be visible or available through helper text.

#### Responsive behavior

Text buttons may become icon + tooltip only when the icon is familiar and labelled.

#### Loading behavior

Replace label or append spinner without changing button width dramatically.

#### Error behavior

Button does not own errors. Show errors through InlineError, Toast, or Dialog.

#### Testing requirements

Verify click, keyboard activation, disabled/loading behavior, accessible label.

#### Do

- Keep one primary CTA per local context.

#### Don't

- Use primary styling for row actions.

### `ChatComposer`

#### Purpose

Capture chat or agent input and submit the main workspace action.

#### When to use

Use at the bottom of Chat and Agent workspaces.

#### When not to use

Do not use for search, debug query, document upload, or settings fields.

#### Anatomy

- Helper/status line.
- Textarea.
- Send/Run button.
- Optional disabled reason.
- Optional attachment/temp file entry near but not inside core input.

#### Variants

- `chat`
- `agent`
- `tempFileBlocked`

#### Sizes

- `default`
- `compactMobile`

#### States

- Empty.
- Typing.
- Focused.
- Disabled.
- Sending.
- Error nearby.

#### Props / data contract

- `value`.
- `placeholder`.
- `isSending`.
- `disabledReason`.
- `mode`.
- `onChange`.
- `onSubmit`.

#### Token usage

- `composer-max-width`
- `font-size-body`
- `line-height-body`
- `radius-xl`
- `shadow-sm`
- focus tokens.
- spacing tokens.

#### Keyboard behavior

Enter submits. Shift+Enter inserts newline. Escape may blur only if it does not lose text.

#### Accessibility

Textarea needs accessible label. Disabled reason must be visible. Submit button needs accessible name.

#### Responsive behavior

Full width on mobile with safe-area bottom support. Textarea grows within a bounded height.

#### Loading behavior

Show streaming/sending state. Prevent duplicate submit.

#### Error behavior

Inline error appears above or near composer only when the error blocks send, such as missing temp file.

#### Testing requirements

Verify Enter/Shift+Enter, disabled reason, send button state, mobile width, input preservation on error.

#### Do

- Make composer the primary input.

#### Don't

- Put advanced settings inside the composer.

### `FileUploadArea`

#### Purpose

Select and upload supported files.

#### When to use

Use for KB document upload and temp file upload.

#### When not to use

Do not use for import ZIP if the workflow requires different copy and validation; use `ImportControl`.

#### Anatomy

- Native file input.
- File type hint.
- Selected filename.
- Upload button.
- Status text.
- Optional progress.

#### Variants

- `knowledgeDocument`
- `tempFile`

#### Sizes

- `default`
- `compact`

#### States

- Empty.
- File selected.
- Uploading.
- Success.
- Error.
- Disabled.

#### Props / data contract

- `accept`.
- `selectedFile`.
- `isUploading`.
- `status`.
- `onSelectFile`.
- `onUpload`.
- `onClear`.

#### Token usage

- input tokens.
- spacing tokens.
- status color tokens.
- border tokens.

#### Keyboard behavior

Native file input must be keyboard reachable. Upload button follows standard button behavior.

#### Accessibility

Use real `input type=file`. Associate label and helper text. Status should be announced when possible.

#### Responsive behavior

Stacks vertically on mobile.

#### Loading behavior

Disable upload button after request starts. Keep selected filename visible.

#### Error behavior

Show inline error in the upload area.

#### Testing requirements

Verify native file picker is reachable, selected filename appears, button enables, success clears input when appropriate.

#### Do

- Keep real file input accessible.

#### Don't

- Hide file input behind an inaccessible fake button.

### `SelectField`

#### Purpose

Let users choose among bounded options such as language, KB, mode, model, or prompt.

#### When to use

Use when the option set is known and relatively small.

#### When not to use

Do not use for free-form search, message input, or large lists without search.

#### Anatomy

- Label.
- Select control.
- Optional helper.
- Optional error.

#### Variants

- `default`
- `compact`

#### Sizes

- `sm`
- `md`

#### States

- Default.
- Focused.
- Disabled.
- Error.
- Loading options.

#### Props / data contract

- `label`.
- `value`.
- `options`.
- `disabled`.
- `error`.
- `onChange`.

#### Token usage

- input, border, focus, text, spacing tokens.

#### Keyboard behavior

Native select keyboard behavior or accessible custom equivalent.

#### Accessibility

Visible label or `aria-label` required.

#### Responsive behavior

Full width in narrow panels.

#### Loading behavior

Disable while options load and show helper text.

#### Error behavior

Inline field error.

#### Testing requirements

Verify options, selected state, disabled state, label association.

#### Do

- Use for bounded choices.

#### Don't

- Use disabled selects as static labels when plain text is clearer.

## 5. Feedback Components

### `InlineError`

#### Purpose

Show recoverable errors close to the failed action.

#### When to use

Use for chat errors, upload failures, form validation, tool failures, and system dependency row errors.

#### When not to use

Do not use for success messages or global background notices.

#### Anatomy

- Error title or message.
- Optional description.
- Optional retry action.

#### Variants

- `danger`
- `warning`

#### Sizes

- `default`
- `compact`

#### States

- Visible.
- With action.

#### Props / data contract

- `message`.
- `description`.
- `actionLabel`.
- `onAction`.
- `tone`.

#### Token usage

- danger/warning tokens.
- border tokens.
- radius tokens.
- spacing tokens.

#### Keyboard behavior

Action button follows standard button behavior.

#### Accessibility

Use `role=alert` only for urgent errors; otherwise use `aria-live=polite`.

#### Responsive behavior

Wrap text and keep action below message on mobile.

#### Loading behavior

If retry is running, action enters loading state.

#### Error behavior

Not applicable.

#### Testing requirements

Verify message visibility, action, screen reader announcement level.

#### Do

- Place errors where users can recover.

#### Don't

- Show raw stack traces.

### `Toast`

#### Purpose

Show lightweight completion or non-blocking feedback.

#### When to use

Use for feedback saved, export completed, reindex completed, import completed, and secondary action notices.

#### When not to use

Do not use as the only error for chat, upload, agent, or form failures.

#### Anatomy

- Status icon.
- Title/message.
- Optional action.
- Close control.

#### Variants

- `success`
- `error`
- `warning`
- `info`

#### Sizes

Not applicable.

#### States

- Entering.
- Visible.
- Exiting.
- Paused on hover/focus.

#### Props / data contract

- `id`.
- `variant`.
- `message`.
- `action`.
- `duration`.
- `onDismiss`.

#### Token usage

- semantic color tokens.
- `z-toast`.
- motion tokens.
- shadow and radius tokens.

#### Keyboard behavior

Close/action controls are keyboard reachable.

#### Accessibility

Use `aria-live=polite` for success/info and assertive only for urgent errors.

#### Responsive behavior

Desktop top-right. Mobile safe-area aware bottom or top stack.

#### Loading behavior

Not applicable.

#### Error behavior

Error variant stays longer and may include action.

#### Testing requirements

Verify stacking, dismissal, keyboard focus, and no duplicate spam.

#### Do

- Keep toast copy short.

#### Don't

- Stack unlimited toasts.

### `Skeleton`

#### Purpose

Reserve space while known content loads.

#### When to use

Use for conversation rows, document rows, source cards, and system sections.

#### When not to use

Do not use for unknown one-off operations or streaming answer generation.

#### Anatomy

- Shape block.
- Optional repeated rows.

#### Variants

- `text`
- `row`
- `card`
- `table`

#### Sizes

- `sm`
- `md`
- `lg`

#### States

- Loading.
- Reduced-motion static.

#### Props / data contract

- `variant`.
- `count`.
- `size`.

#### Token usage

- background subtle tokens.
- radius tokens.
- motion tokens.

#### Keyboard behavior

Not applicable.

#### Accessibility

Mark decorative skeletons `aria-hidden=true`. Parent region should expose loading state.

#### Responsive behavior

Adapts to container width.

#### Loading behavior

This is the loading component.

#### Error behavior

Replace with error state if load fails.

#### Testing requirements

Verify skeleton does not shift layout when content loads.

#### Do

- Use where layout is predictable.

#### Don't

- Use shimmer when reduced motion is requested.

## 6. Display and Data Components

### `StatusBadge`

#### Purpose

Communicate compact semantic status.

#### When to use

Use for KB file status, system health, dependency status, model/tool state, and agent step status.

#### When not to use

Do not use as a decorative pill or navigation selected state.

#### Anatomy

- Optional dot/icon.
- Label.

#### Variants

- `ok`
- `healthy`
- `indexed`
- `uploaded`
- `running`
- `pending`
- `degraded`
- `failed`
- `error`
- `unavailable`

#### Sizes

- `sm`
- `md`

#### States

Semantic variants only.

#### Props / data contract

- `status`.
- `label`.
- `showDot`.

#### Token usage

- success, warning, danger, info, muted tokens.
- badge typography.
- radius-pill.

#### Keyboard behavior

Not applicable.

#### Accessibility

Status text must be visible. Do not rely on color alone.

#### Responsive behavior

Can shrink to text + dot if label remains available.

#### Loading behavior

Use `pending` or skeleton if status unknown.

#### Error behavior

Use failed/error variants.

#### Testing requirements

Verify every backend status maps to a known label.

#### Do

- Reuse semantic statuses.

#### Don't

- Invent a new color per status.

### `SourceCard`

#### Purpose

Show a readable source citation detail.

#### When to use

Use in SourcesPanel and source detail contexts.

#### When not to use

Do not use for Retrieval Debug score-heavy output; use `RetrievalResultCard`.

#### Anatomy

- Index.
- Title/file/URL label.
- Preview text.
- Optional open link.
- Optional chunk label.

#### Variants

- `file`
- `url`
- `historicalMissing`

#### Sizes

Not applicable.

#### States

- Default.
- Hover for clickable URL.
- Empty/missing.

#### Props / data contract

- `index`.
- `title`.
- `fileName`.
- `url`.
- `source`.
- `preview`.
- `chunkId`.

#### Token usage

- source/reference surface tokens.
- typography tokens.
- border subtle tokens.
- radius-lg.

#### Keyboard behavior

URL links are keyboard reachable.

#### Accessibility

Links open in new tab with safe `rel`. Label must be readable without URL alone.

#### Responsive behavior

Preview clamps on narrow panels with full content available in detail when needed.

#### Loading behavior

Use `Skeleton` source card.

#### Error behavior

Missing historical sources uses empty text, not error styling.

#### Testing requirements

Verify URL source clickable, file source label, preview, and no debug fields in normal mode.

#### Do

- Use human-readable citation labels.

#### Don't

- Lead with `distance`, `chunk_id`, or raw database fields.

### `DataTable`

#### Purpose

Show dense comparable data.

#### When to use

Use for document lists and future system/tool tables when comparison matters.

#### When not to use

Do not use for chat, narrative agent trace, or short mobile-only lists.

#### Anatomy

- Header.
- Rows.
- Cells.
- Status cell.
- Actions cell.
- Empty/loading/error state.

#### Variants

- `document`
- `dependency`
- `tool`

#### Sizes

- `default`
- `dense`

#### States

- Loading.
- Empty.
- Row hover.
- Row selected.
- Row action loading.
- Error.

#### Props / data contract

- `columns`.
- `rows`.
- `getRowId`.
- `selectedRowId`.
- `actions`.
- `isLoading`.
- `error`.

#### Token usage

- table/list row height tokens when added.
- border subtle tokens.
- body small typography.
- status tokens.

#### Keyboard behavior

Focusable row actions. If rows are selectable, Enter/Space selects.

#### Accessibility

Use semantic table for real tables. Provide column headers. Row actions need labels.

#### Responsive behavior

Transforms to list rows on tablet/mobile.

#### Loading behavior

Use table skeleton.

#### Error behavior

Show table-level inline error above rows.

#### Testing requirements

Verify row actions, status labels, keyboard navigation, mobile transformation.

#### Do

- Use for comparison.

#### Don't

- Put raw JSON in cells.

## 7. Chat Components

### `ChatMessageList`

#### Purpose

Render ordered user, assistant, streaming, and agent messages.

#### When to use

Use inside Chat and Agent conversation stream.

#### When not to use

Do not use for source lists, agent timeline, or document history.

#### Anatomy

- Message list.
- Message item.
- Role label.
- Content.
- Metadata hint.
- Actions.
- Streaming item.

#### Variants

- `chat`
- `agent`

#### Sizes

Not applicable.

#### States

- Empty delegated to `EmptyState`.
- Loading delegated to parent.
- Selected assistant message.
- Streaming.

#### Props / data contract

- `messages`.
- `streamingMessage`.
- `selectedAssistantMessageId`.
- `onSelectAssistantMessage`.

#### Token usage

- `chat-message-max-width`.
- body typography.
- spacing tokens.
- selected surface tokens.

#### Keyboard behavior

Selectable assistant messages must be keyboard reachable in final implementation.

#### Accessibility

Message stream should have a labelled region. Streaming content should use polite live updates.

#### Responsive behavior

Message width becomes full available width on mobile.

#### Loading behavior

Streaming message shows typing/streaming indicator.

#### Error behavior

Failed assistant message should render an inline error block near message content.

#### Testing requirements

Verify order, selected assistant sources, streaming display, feedback controls.

#### Do

- Keep answer text readable.

#### Don't

- Render messages as dense chat bubbles.

### `AssistantMessage`

#### Purpose

Render an assistant answer with optional sources and feedback.

#### When to use

Use for all assistant messages in normal Chat and final Agent answer when stored as message.

#### When not to use

Do not use for tool observations or raw traces.

#### Anatomy

- Role label.
- Answer body.
- Source reference summary.
- Feedback controls.
- Optional error.

#### Variants

- `default`
- `streaming`
- `error`
- `agent`

#### Sizes

Not applicable.

#### States

- Default.
- Selected.
- Streaming.
- Error.
- Feedback saved.

#### Props / data contract

- `id`.
- `content`.
- `sources`.
- `metadata`.
- `feedbackScore`.
- `isSelected`.
- `onSelect`.
- `onFeedback`.

#### Token usage

- body typography.
- source/reference tokens.
- spacing tokens.
- selected surface tokens.

#### Keyboard behavior

If selectable, Enter/Space selects the message.

#### Accessibility

Do not hide role. Feedback buttons require labels. Streaming uses polite live region.

#### Responsive behavior

Body width follows `chat-message-max-width` or full width on mobile.

#### Loading behavior

Streaming variant shows cursor/typing indicator.

#### Error behavior

Error variant shows inline error and retry action when supported.

#### Testing requirements

Verify selected state updates SourcesPanel and feedback is available only when message id exists.

#### Do

- Put feedback after the answer.

#### Don't

- Put source debug scores in normal assistant message.

### `FeedbackControls`

#### Purpose

Let users rate assistant messages.

#### When to use

Use below assistant messages with persisted `message_id`.

#### When not to use

Do not show for user messages, streaming message before done, or messages without backend id.

#### Anatomy

- Like button.
- Dislike button.
- Saved state.
- Optional reason prompt trigger.

#### Variants

- `compact`

#### Sizes

Not applicable.

#### States

- Unset.
- Like selected.
- Dislike selected.
- Saving.
- Error.

#### Props / data contract

- `messageId`.
- `feedbackScore`.
- `onSubmitFeedback`.

#### Token usage

- ghost/secondary button tokens.
- success/danger subtle tokens for saved state.
- caption typography.

#### Keyboard behavior

Buttons are keyboard reachable.

#### Accessibility

Buttons need clear labels: Like answer, Dislike answer.

#### Responsive behavior

Stay inline unless narrow width requires wrapping.

#### Loading behavior

Disable duplicate submit while saving.

#### Error behavior

Show inline compact error or toast only if action context remains clear.

#### Testing requirements

Verify like/dislike POST `/chat/feedback`, saved state, no duplicate accidental submit.

#### Do

- Keep low visual emphasis.

#### Don't

- Show feedback before assistant message id is known.

## 8. Knowledge Components

### `KnowledgeBasePanel`

#### Purpose

Coordinate KB selection, stats, upload, import/export, and document list.

#### When to use

Use in Knowledge workspace.

#### When not to use

Do not embed entire KB management inside Chat header or System.

#### Anatomy

- Current KB.
- KB list/select.
- Stats summary.
- Upload area.
- Import/export area.
- Refresh action.
- Document list/table.
- Action status.

#### Variants

- `workspace`
- `compactPanel`

#### Sizes

Not applicable.

#### States

- Loading.
- Empty KB list.
- Empty documents.
- Uploading.
- Importing/exporting.
- Document action loading.
- Error.

#### Props / data contract

- `knowledgeBases`.
- `currentKb`.
- `documents`.
- action callbacks for switch, upload, import, export, refresh, download, reindex, delete.
- status/error values.

#### Token usage

- surface tokens.
- status tokens.
- spacing tokens.
- list/table tokens.

#### Keyboard behavior

All document and KB actions must be buttons or links. Row menus must support Escape.

#### Accessibility

Use labelled regions. File inputs need labels. Delete requires confirmation dialog.

#### Responsive behavior

Desktop uses workspace/table. Mobile uses stacked sections and document list rows.

#### Loading behavior

Use skeleton for KB/documents. Button actions show inline loading.

#### Error behavior

Show errors near the failed section: upload, import/export, document action, or list load.

#### Testing requirements

Verify KB switch calls `/switch_kb`, upload, document refresh, row actions, import/export, and status display.

#### Do

- Keep documents central.

#### Don't

- Make import/export primary over upload.

### `DocumentRow`

#### Purpose

Represent one KB document and its operational state.

#### When to use

Use inside `DocumentTable` or mobile document list.

#### When not to use

Do not use for chunks or sources.

#### Anatomy

- Filename.
- Metadata.
- Status badge.
- Chunk count.
- Chunk parameters.
- Row actions.
- Optional error summary.

#### Variants

- `tableRow`
- `listCard`

#### Sizes

- `default`
- `dense`

#### States

- Default.
- Hover.
- Selected.
- Indexed.
- Uploaded.
- Failed.
- Action loading.

#### Props / data contract

- `filename`.
- `status`.
- `docsCount`.
- `chunkSize`.
- `chunkOverlap`.
- `uploadPath`.
- `contentPath`.
- `error`.
- action callbacks.

#### Token usage

- table/list tokens.
- status tokens.
- text/caption tokens.
- border subtle tokens.

#### Keyboard behavior

Row action buttons reachable. If row selectable, Enter/Space selects.

#### Accessibility

Actions need filename in accessible name.

#### Responsive behavior

Long filename truncates with detail access.

#### Loading behavior

Action buttons show loading and disable repeated clicks.

#### Error behavior

Failed documents show error summary and detail access.

#### Testing requirements

Verify stable `data-testid` naming, row actions, status, and long filename behavior.

#### Do

- Keep row actions secondary.

#### Don't

- Delete without confirmation.

## 9. Agent Components

### `AgentTracePanel`

#### Purpose

Show human-readable agent planning, tool calls, observations, final answer, and optional raw trace.

#### When to use

Use only in Agent mode or selected agent message detail.

#### When not to use

Do not show in normal local KB/search/temp chat.

#### Anatomy

- Heading.
- Running status.
- Planner summary.
- Timeline steps.
- Tool call summary.
- Tool result/observation.
- Final answer.
- Raw trace disclosure.

#### Variants

- `running`
- `completed`
- `failed`
- `historical`

#### Sizes

Not applicable.

#### States

- Empty.
- Running.
- Tool running.
- Tool failed.
- Completed.
- Error.

#### Props / data contract

- `isRunning`.
- `error`.
- `result`: answer, tool_call, tool_result, planner, steps, trace, tool_count.
- `streamStatus`.
- `streamTokenText`.

#### Token usage

- timeline spacing tokens.
- status tokens.
- mono typography for raw payloads.
- surface and border tokens.

#### Keyboard behavior

Details disclosures must be keyboard reachable.

#### Accessibility

Timeline status must be textual, not icon-only. Running updates should be polite.

#### Responsive behavior

Timeline stacks vertically. Raw payloads scroll horizontally or wrap safely.

#### Loading behavior

Running state uses timeline progress, not full spinner.

#### Error behavior

Tool errors appear at failed step and in result summary when needed.

#### Testing requirements

Verify calculator, kb_search, sqlite, filesystem, browser_search/browser_read observations render correctly.

#### Do

- Format tool results by tool type.

#### Don't

- Lead with raw JSON.

### `ToolObservation`

#### Purpose

Render one tool result in a consistent human-readable format.

#### When to use

Use inside Agent timeline and trace panel.

#### When not to use

Do not use for normal sources or KB document rows.

#### Anatomy

- Tool label.
- Arguments summary.
- Result summary.
- Error block.
- Optional raw detail.

#### Variants

- `calculator`
- `current_time`
- `kb_search`
- `sqlite_readonly_query`
- `filesystem_readonly_read`
- `browser_search`
- `browser_read`
- `generic`

#### Sizes

Not applicable.

#### States

- Success.
- Error.
- Truncated.
- Empty.

#### Props / data contract

- `toolName`.
- `arguments`.
- `result`.
- `error`.
- `metadata`.

#### Token usage

- status tokens.
- mono typography for raw detail.
- surface subtle tokens.
- spacing tokens.

#### Keyboard behavior

Raw detail disclosure supports Enter/Space.

#### Accessibility

Tool result summary must be readable without opening raw detail.

#### Responsive behavior

Tables/rows inside observations collapse to stacked metadata on mobile.

#### Loading behavior

Tool running state belongs to parent timeline.

#### Error behavior

Show tool error prominently inside observation.

#### Testing requirements

Verify each supported tool variant and truncated content flag.

#### Do

- Summarize before raw detail.

#### Don't

- Render all tools as JSON.

## 10. System Components

### `SystemOverview`

#### Purpose

Show runtime health, provider/model status, dependencies, tools, and MCP status.

#### When to use

Use in System workspace.

#### When not to use

Do not use as a general dashboard or settings form.

#### Anatomy

- Overall health.
- Service/version.
- Provider/model.
- Dependency list.
- Tool registry summary.
- MCP summary.
- Refresh action.
- Detail selection.

#### Variants

- `healthy`
- `degraded`
- `failure`

#### Sizes

Not applicable.

#### States

- Loading.
- Ready.
- Degraded.
- Error.
- MCP unavailable.

#### Props / data contract

- `/health` data.
- `/health/deps` data.
- `/models` data.
- `/agent/tools` data.
- `/agent/mcp/servers` data.
- `/agent/mcp/tools` data.
- `onRefresh`.

#### Token usage

- status tokens.
- list/table tokens.
- heading/text tokens.
- surface tokens.

#### Keyboard behavior

Refresh and detail actions are reachable. Lists follow standard list/table behavior.

#### Accessibility

Do not expose API keys. Status uses readable text.

#### Responsive behavior

Overview stacks before details on mobile.

#### Loading behavior

Sections can load independently with skeleton.

#### Error behavior

Page-level error only when system APIs are unavailable; dependency-level errors stay inline.

#### Testing requirements

Verify `/health`, `/health/deps`, `/models`, tools, MCP data render without secrets.

#### Do

- Show factual system state.

#### Don't

- Add settings controls backend cannot save.

## 11. Overlay Components

### `ConfirmDialog`

#### Purpose

Confirm destructive or blocking user decisions.

#### When to use

Use for delete conversation, delete document, delete KB, and other irreversible actions.

#### When not to use

Do not use for simple success messages or non-blocking status.

#### Anatomy

- Backdrop.
- Dialog container.
- Title.
- Description.
- Optional body.
- Secondary action.
- Optional primary action.
- Danger action.
- Inline error.

#### Variants

- `danger`
- `confirm`

#### Sizes

- `sm`
- `md`

#### States

- Open.
- Loading.
- Error.

#### Props / data contract

- `isOpen`.
- `title`.
- `description`.
- `body`.
- `cancelLabel`.
- `confirmLabel`.
- `variant`.
- `isLoading`.
- `error`.
- `onCancel`.
- `onConfirm`.

#### Token usage

- `z-dialog`.
- dialog width tokens when added.
- surface/elevated tokens.
- danger tokens.
- radius-xl.
- shadow-md.

#### Keyboard behavior

Escape cancels unless loading. Tab is trapped inside dialog. Enter activates focused action only.

#### Accessibility

Use `role=dialog`, `aria-modal=true`, `aria-labelledby`, and optional `aria-describedby`. Return focus to trigger on close.

#### Responsive behavior

Centered on desktop. Bottom sheet or full-width safe-margin dialog on mobile.

#### Loading behavior

Disable actions except possibly Cancel when safe. Show loading label.

#### Error behavior

Show inline error inside dialog and keep it open.

#### Testing requirements

Verify focus trap, Escape, labels, confirm/cancel callbacks, loading and error.

#### Do

- Put danger action farthest right.

#### Don't

- Close automatically after failed confirm.

### `ContextPanel`

#### Purpose

Provide workspace-specific secondary detail.

#### When to use

Use for Chat sources/retrieval, Agent plan/tools/trace, Knowledge document/chunks/stats, and System details.

#### When not to use

Do not use for primary workspace content or blocking decisions.

#### Anatomy

- Header.
- Tabs.
- Body.
- Empty state.
- Collapse control.

#### Variants

- `chat`
- `agent`
- `knowledge`
- `system`

#### Sizes

Uses `context-panel-width`; collapses responsively.

#### States

- Empty.
- Loading.
- Active tab.
- Collapsed.
- Error.

#### Props / data contract

- `workspace`.
- `tabs`.
- `activeTab`.
- `onChangeTab`.
- `isCollapsed`.
- `onCollapse`.
- `children`.

#### Token usage

- context width token.
- surface tokens.
- border tokens.
- tab/list tokens.
- z-index overlay tokens on mobile.

#### Keyboard behavior

Tabs support arrow-key navigation in final implementation. Collapse button is keyboard reachable.

#### Accessibility

Use `aside` with label. Tabs use `tablist`, `tab`, and `tabpanel` semantics.

#### Responsive behavior

Desktop fixed side panel. Tablet collapsible sheet. Mobile bottom sheet or separate detail page.

#### Loading behavior

Show scoped skeleton/loading in panel body.

#### Error behavior

Show inline panel error.

#### Testing requirements

Verify tab selection, selected item detail priority, collapse behavior, mobile access.

#### Do

- Keep one Context Panel model across product.

#### Don't

- Duplicate with multiple drawers and modals for the same detail.

## 12. Testing Standard for All Components

Every implemented component must be tested against:

- Semantic HTML and accessible labels.
- Keyboard operation.
- Loading state.
- Error state.
- Disabled state when applicable.
- Responsive behavior at mobile, tablet, and desktop.
- No raw API key or secret display.
- No unsupported fake action.
- No hardcoded raw hex color when a token exists.
- No one-off font size, radius, shadow, or spacing unless documented.

Components with API-backed actions must also verify:

- Correct endpoint.
- Correct payload.
- Success state.
- Failure state.
- No duplicate submission while loading.

Components with `data-testid` must keep stable test ids across refactors unless tests are intentionally updated.
