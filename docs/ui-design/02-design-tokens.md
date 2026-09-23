# Mini ChatChat Design Tokens v1

These tokens translate the Mini ChatChat Design Bible into implementation-ready CSS variables and React component standards. They are for the light theme only. Do not introduce component-level one-off values unless this document is updated first.

## 1. Color Tokens

Mini ChatChat uses a restrained product palette: mostly neutral, a small amount of surface contrast, and rare accent. The brand should feel calm and trustworthy, not saturated or decorative.

| Token | Hex value | Usage | Do not use for |
| --- | --- | --- | --- |
| `color-bg-app` | `#F7F7F5` | App canvas and page background. | Buttons, badges, message content. |
| `color-bg-sidebar` | `#FBFBFA` | Sidebar and navigation rail. | Main chat content background. |
| `color-bg-surface` | `#FFFFFF` | Primary panels, cards, composer, dialogs. | Page background or selected states. |
| `color-bg-subtle` | `#F3F4F2` | Secondary blocks, inactive mode cards, quiet metadata zones. | Main CTA or danger states. |
| `color-bg-elevated` | `#FFFFFF` | Composer, popovers, dropdowns, dialogs. | Regular list rows. |
| `color-bg-hover` | `#EFF1F3` | Hover on quiet buttons, nav rows, selectable list items. | Persistent selected states. |
| `color-bg-selected` | `#E9EDF2` | Current nav item, selected conversation, active mode. | Alerts or destructive actions. |
| `color-text-primary` | `#1F2933` | Main text, chat answer text, page headings. | Disabled text. |
| `color-text-secondary` | `#4B5563` | Secondary labels, supporting copy, source descriptions. | Main answer paragraphs. |
| `color-text-muted` | `#778190` | Timestamps, metadata, hints, source numbering. | Primary labels or errors. |
| `color-text-disabled` | `#A6ADB7` | Disabled controls and unavailable states. | Placeholder text for active inputs. |
| `color-text-inverse` | `#FFFFFF` | Text on brand/danger filled buttons only. | Normal surfaces. |
| `color-border-default` | `#DDE2E8` | Inputs, cards, list rows, panels. | Focus rings. |
| `color-border-subtle` | `#ECEFF3` | Dividers, low-emphasis sections, quiet cards. | Form focus or active selection. |
| `color-border-strong` | `#C8D0DA` | Hovered inputs, selected rows, stronger separators. | Default dense lists. |
| `color-border-focus` | `#6E7F99` | Input focus, selected control focus ring. | Static borders. |
| `color-brand-primary` | `#46556D` | Primary CTA, send button, brand mark, active high-importance control. | Large backgrounds, sidebar, secondary buttons. |
| `color-brand-hover` | `#53627A` | Hover state for primary CTA. | Disabled or inactive states. |
| `color-brand-active` | `#313C4F` | Pressed primary CTA, active brand mark contrast. | Body text or card backgrounds. |
| `color-brand-soft` | `#EEF1F5` | Active nav/mode background, selected conversation. | Success/warning/danger status. |
| `color-success` | `#1F9D62` | Healthy, indexed, completed, successful action. | General active selection. |
| `color-success-soft` | `#EAF8EF` | Success badge background. | Page sections or cards. |
| `color-warning` | `#B7791F` | Degraded, pending, needs attention. | Destructive errors. |
| `color-warning-soft` | `#FFF5DF` | Warning badge/background. | Normal hints. |
| `color-danger` | `#D6453D` | Delete, failed, error text. | General primary CTA. |
| `color-danger-soft` | `#FFF0EE` | Error block, danger badge, delete hover base. | Non-destructive warnings. |
| `color-info` | `#3B75C3` | Informational status and optional inline note. | Main brand color. |
| `color-info-soft` | `#EEF6FF` | Info badge background. | Large page surfaces. |

## 2. Typography Tokens

Use a small type scale. If two text styles feel almost identical, use one token.

| Token | Value | Usage |
| --- | --- | --- |
| `font-family-sans` | `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | All product UI and chat text. |
| `font-family-mono` | `"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace` | Code snippets, SQL, debug payloads, tool arguments. |
| `font-size-display` | `48px` | Rare product-level hero only. Avoid inside panels. |
| `font-size-heading` | `36px` | Page titles: Chat, Knowledge Base, System. |
| `font-size-title` | `22px` | Section titles and panel headings. |
| `font-size-body` | `15px` | Main chat answer text and normal paragraphs. |
| `font-size-body-small` | `14px` | Supporting UI copy, source preview, document metadata. |
| `font-size-label` | `12px` | Form labels, metadata labels, section kicker text. |
| `font-size-caption` | `12px` | Timestamps, hint text, secondary source details. |
| `font-size-badge` | `11px` | Status badges and compact pills. |
| `font-weight-regular` | `400` | Body copy. |
| `font-weight-medium` | `500` | Metadata with slight emphasis. |
| `font-weight-semibold` | `650` | Button text, labels, selected row title. |
| `font-weight-bold` | `760` | Page headings and important stat numbers. |
| `line-height-display` | `1.04` | Display and page headings. |
| `line-height-heading` | `1.12` | H1/H2 section titles. |
| `line-height-body` | `1.62` | Chat answers and readable content. |
| `line-height-compact` | `1.32` | Labels, badges, buttons, metadata. |

## 3. Spacing Tokens

All layout should follow an 8px grid. `4px` is allowed only for tight internal spacing.

| Token | Value | Usage |
| --- | --- | --- |
| `space-1` | `4px` | Tiny icon/text gaps, badge internals. |
| `space-2` | `8px` | Control spacing, compact list gaps. |
| `space-3` | `12px` | Button internal padding, form field gaps. |
| `space-4` | `16px` | Card padding, message internals, sidebar row gaps. |
| `space-5` | `20px` | Panel padding and composer padding. |
| `space-6` | `24px` | Section spacing and page group gaps. |
| `space-8` | `32px` | Page header-to-content spacing, large panel gaps. |
| `space-10` | `40px` | Major workspace rhythm. |
| `space-12` | `48px` | Large page spacing. |
| `space-16` | `64px` | Rare top-level page separation. |

Usage rules:

- Control spacing: `space-2` to `space-3`.
- Card padding: `space-4` to `space-5`.
- Section spacing: `space-6` to `space-8`.
- Page spacing: `space-8` to `space-12`.
- Layout gap: `space-4` for dense workspaces, `space-6` for primary page grids.

## 4. Radius Tokens

Do not use one oversized radius everywhere. Radius communicates component type.

| Token | Value | Usage |
| --- | --- | --- |
| `radius-sm` | `8px` | Small badges, icon buttons, compact menu items. |
| `radius-md` | `12px` | Buttons, inputs, dropdowns, mode cards. |
| `radius-lg` | `16px` | Cards, document rows, source references. |
| `radius-xl` | `24px` | Composer, primary panels, dialogs. |
| `radius-pill` | `999px` | Badges, status pills, compact toolbar buttons. |
| `radius-circle` | `50%` | Avatars and circular icon marks only. |

Component mapping:

- Button: `radius-md`, or `radius-pill` for compact toolbar/pills.
- Input: `radius-md`.
- Card: `radius-lg`.
- Dialog: `radius-xl`.
- Badge: `radius-pill`.
- Avatar/brand dot: `radius-circle` or `radius-md` when square mark is intended.

## 5. Shadow Tokens

Shadows are functional elevation, not decoration.

| Token | Value | Usage |
| --- | --- | --- |
| `shadow-none` | `none` | Sidebar, topbar, flat lists, default system cards. |
| `shadow-xs` | `0 1px 2px rgba(31, 41, 51, 0.04)` | Subtle list hover, small elevated rows. |
| `shadow-sm` | `0 8px 20px rgba(31, 41, 51, 0.06)` | Composer idle, popover, focused source card. |
| `shadow-md` | `0 18px 48px rgba(31, 41, 51, 0.08)` | Dialog, floating panel. |
| `shadow-lg` | `0 30px 80px rgba(31, 41, 51, 0.10)` | Rare modal overlay only. |
| `shadow-focus` | `0 0 0 4px rgba(70, 85, 109, 0.12)` | Keyboard focus and active input. |

Allowed:

- Composer: `shadow-sm`.
- Dialog/popover: `shadow-md`.
- Focus state: `shadow-focus`.

Forbidden:

- Repeated document rows with heavy shadows.
- Sidebar and topbar decorative shadows.
- Every card using `shadow-md` or `shadow-lg`.

## 6. Border Tokens

| Token | Value | Usage |
| --- | --- | --- |
| `border-width-default` | `1px` | Inputs, cards, list rows, dividers. |
| `border-width-strong` | `2px` | Rare selected/focused state when shadow is insufficient. |
| `border-style-default` | `solid` | All standard borders. |

Usage:

- List: use subtle bottom border or row outline, not both.
- Table: horizontal dividers only unless data density requires full grid.
- Input: default border + focus border token.
- Card: default border only when surface separation is necessary.
- Divider: `color-border-subtle`.

## 7. Motion Tokens

Motion should clarify state. It should not entertain.

| Token | Value | Usage |
| --- | --- | --- |
| `motion-duration-fast` | `120ms` | Hover, pressed, small icon changes. |
| `motion-duration-normal` | `190ms` | Dropdown, source card hover, message entry. |
| `motion-duration-slow` | `280ms` | Dialog, drawer, larger collapse/expand. |
| `motion-ease-standard` | `cubic-bezier(0.16, 1, 0.3, 1)` | Default UI transitions. |
| `motion-ease-emphasized` | `cubic-bezier(0.2, 0.8, 0.2, 1)` | Dialog and agent timeline state changes. |

Usage:

- Hover: fast.
- Dropdown: normal.
- Dialog: slow.
- Collapse: normal to slow.
- Streaming state: cursor blink, no large movement.
- Agent timeline: subtle fade/slide only.

Reduced motion:

- All non-essential animation must be disabled under `prefers-reduced-motion: reduce`.
- Streaming cursor may remain static.
- Skeleton shimmer should stop or reduce to near-static.

## 8. Size Tokens

These values define the layout proportions for the current product.

| Token | Value | Usage |
| --- | --- | --- |
| `control-height-sm` | `32px` | Small toolbar buttons, badges, compact selects. |
| `control-height-md` | `40px` | Standard buttons, inputs, selects. |
| `control-height-lg` | `48px` | Primary actions and larger controls. |
| `icon-size-sm` | `16px` | Inline icons and metadata icons. |
| `icon-size-md` | `20px` | Button icons and nav glyphs. |
| `icon-size-lg` | `28px` | Brand mark internals and empty states. |
| `sidebar-width` | `236px` | Desktop primary navigation rail. |
| `sidebar-collapsed-width` | `72px` | Tablet/compact rail. |
| `context-panel-width` | `360px` | Sources/debug/agent context panel. |
| `content-max-width` | `1320px` | Maximum workspace content width. |
| `chat-message-max-width` | `760px` | Assistant message reading width. |
| `composer-max-width` | `760px` | Chat composer width aligned with answer text. |

Intent:

- Sidebar should orient but not dominate.
- Chat content should remain readable, not stretch full screen.
- Context panel should be useful but secondary.
- Buttons and inputs should use consistent heights.

## 9. Z-index Tokens

| Token | Value | Usage |
| --- | --- | --- |
| `z-base` | `0` | Normal document flow. |
| `z-sticky` | `10` | Sticky topbar or composer when needed. |
| `z-dropdown` | `30` | Dropdown menu, conversation menu. |
| `z-overlay` | `50` | Drawer/backdrop overlay. |
| `z-dialog` | `70` | Dialog/confirm modal. |
| `z-toast` | `90` | Toast notifications. |
| `z-tooltip` | `100` | Tooltips. |

Rules:

- Components must not invent arbitrary z-index values.
- If a new layering need appears, update this document first.

## 10. CSS Variables Example

```css
:root {
  --color-bg-app: #F7F7F5;
  --color-bg-sidebar: #FBFBFA;
  --color-bg-surface: #FFFFFF;
  --color-bg-subtle: #F3F4F2;
  --color-bg-elevated: #FFFFFF;
  --color-bg-hover: #EFF1F3;
  --color-bg-selected: #E9EDF2;

  --color-text-primary: #1F2933;
  --color-text-secondary: #4B5563;
  --color-text-muted: #778190;
  --color-text-disabled: #A6ADB7;
  --color-text-inverse: #FFFFFF;

  --color-border-default: #DDE2E8;
  --color-border-subtle: #ECEFF3;
  --color-border-strong: #C8D0DA;
  --color-border-focus: #6E7F99;

  --color-brand-primary: #46556D;
  --color-brand-hover: #53627A;
  --color-brand-active: #313C4F;
  --color-brand-soft: #EEF1F5;

  --color-success: #1F9D62;
  --color-success-soft: #EAF8EF;
  --color-warning: #B7791F;
  --color-warning-soft: #FFF5DF;
  --color-danger: #D6453D;
  --color-danger-soft: #FFF0EE;
  --color-info: #3B75C3;
  --color-info-soft: #EEF6FF;

  --font-family-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-family-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  --font-size-display: 48px;
  --font-size-heading: 36px;
  --font-size-title: 22px;
  --font-size-body: 15px;
  --font-size-body-small: 14px;
  --font-size-label: 12px;
  --font-size-caption: 12px;
  --font-size-badge: 11px;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 650;
  --font-weight-bold: 760;

  --line-height-display: 1.04;
  --line-height-heading: 1.12;
  --line-height-body: 1.62;
  --line-height-compact: 1.32;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-pill: 999px;
  --radius-circle: 50%;

  --shadow-none: none;
  --shadow-xs: 0 1px 2px rgba(31, 41, 51, 0.04);
  --shadow-sm: 0 8px 20px rgba(31, 41, 51, 0.06);
  --shadow-md: 0 18px 48px rgba(31, 41, 51, 0.08);
  --shadow-lg: 0 30px 80px rgba(31, 41, 51, 0.10);
  --shadow-focus: 0 0 0 4px rgba(70, 85, 109, 0.12);

  --border-width-default: 1px;
  --border-width-strong: 2px;
  --border-style-default: solid;

  --motion-duration-fast: 120ms;
  --motion-duration-normal: 190ms;
  --motion-duration-slow: 280ms;
  --motion-ease-standard: cubic-bezier(0.16, 1, 0.3, 1);
  --motion-ease-emphasized: cubic-bezier(0.2, 0.8, 0.2, 1);

  --control-height-sm: 32px;
  --control-height-md: 40px;
  --control-height-lg: 48px;
  --icon-size-sm: 16px;
  --icon-size-md: 20px;
  --icon-size-lg: 28px;
  --sidebar-width: 236px;
  --sidebar-collapsed-width: 72px;
  --context-panel-width: 360px;
  --content-max-width: 1320px;
  --chat-message-max-width: 760px;
  --composer-max-width: 760px;

  --z-base: 0;
  --z-sticky: 10;
  --z-dropdown: 30;
  --z-overlay: 50;
  --z-dialog: 70;
  --z-toast: 90;
  --z-tooltip: 100;
}
```

## 11. Usage Rules

- Components must not write raw hex colors.
- Components must not introduce one-off font sizes.
- Components must not introduce one-off radius values.
- Components must not introduce one-off shadows.
- New tokens must be added to this document before implementation.
- New components must use existing semantic tokens first.
- Special values must include a comment explaining why they cannot use an existing token.
- Debug UI may use mono typography, but must still use color, spacing, border, and radius tokens.
- Dangerous actions must use danger tokens and confirmation patterns.
- Primary actions must remain rare. If every action looks primary, no action is primary.
