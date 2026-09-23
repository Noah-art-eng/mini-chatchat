# Mini ChatChat Design Bible v1

## 1. Design Philosophy

Mini ChatChat should feel like a calm AI workspace, not an admin dashboard.

The product language is:

- Quiet
- Precise
- Trustworthy
- Source-aware
- Tool-aware
- Local-first
- Professional

The product should not feel decorative. It should feel intentional.

Mature products like ChatGPT, Claude, Perplexity, Notion, Linear, Raycast, Vercel, and Dify share one principle:

They reduce visual noise so the user’s current task becomes obvious.

For Mini ChatChat, the current task is usually:

Ask a question → inspect answer → verify sources → optionally manage knowledge or agent steps.

Everything else should stay secondary.

---

## 2. Information Hierarchy

Default visual priority:

1. Chat content
2. Chat input
3. Sources / citations
4. Current workspace context
5. Sidebar navigation
6. System / settings / debug information

Rules:

- Chat should always be the visual center.
- Sources should support the answer, not compete with it.
- Agent trace should appear only in Agent mode.
- Debug controls should never be primary UI.
- System status should be calm and factual.
- Sidebar should orient, not dominate.

---

## 3. Typography Scale

Use a small, strict type scale.

- Display: Product/page hero only
- Heading: Main page title
- Title: Section title
- Body: Main readable content
- Caption: Metadata, timestamps, secondary hints
- Label: Form labels and field names
- Badge: Compact status text
- Button: Action text

Rules:

- Avoid many similar font sizes.
- Do not use huge type inside dense panels.
- Body text readability matters more than visual drama.
- Labels should be quiet, uppercase only when they are metadata.
- Chat answer text should use comfortable line height.

Recommended hierarchy:

- Display: 44–56px
- Heading: 30–40px
- Title: 18–24px
- Body: 14–16px
- Caption: 12–13px
- Badge/Label: 11–12px

---

## 4. Color System

Target ratio:

- 80% Neutral
- 15% Surface
- 5% Accent

Mini ChatChat should not be blue everywhere.

Color roles:

- Primary: Only active workspace, main send action, selected critical state
- Secondary: Supporting active state or subtle brand accent
- Accent: Rare emphasis
- Success: Completed / indexed / healthy
- Warning: Degraded / needs attention
- Danger: Delete / failed / destructive
- Info: Informational but not urgent
- Neutral: Default UI, text, borders, surfaces

Rules:

- Never use color without meaning.
- Avoid gradients except for brand mark or rare product hero use.
- Do not use pure black for buttons.
- Do not use saturated color for secondary actions.
- Dangerous actions must be visually distinct but not oversized.
- Debug data should not introduce new colors.

---

## 5. Spacing System

Use an 8px grid.

Base spacing:

- 4px: tiny internal gaps
- 8px: compact control spacing
- 16px: normal component padding
- 24px: section spacing
- 32px: page rhythm
- 48px+: large page separation

Rules:

- More whitespace around primary chat content.
- Less spacing inside dense metadata.
- Do not stack equal cards with equal gaps forever.
- Use rhythm: header → content → supporting panel.
- Prefer alignment over decoration.

---

## 6. Surface System

Surface levels:

- Background: app canvas
- Base surface: main content panels
- Raised surface: composer, active cards, dialogs
- Subtle surface: inactive controls, metadata zones
- Critical surface: danger/error only

Rules:

- Not every group needs a card.
- Avoid cards inside cards.
- Use surface changes to communicate importance.
- Chat content should feel lighter than management panels.
- Composer may be slightly raised because it is an active control.
- Sources should feel like reference material, not dashboard widgets.

---

## 7. Shadow System

Shadows should be rare.

Use shadows for:

- Active input
- Floating composer
- Dialog
- Temporary overlay
- Hover only when it clarifies interactivity

Rules:

- Avoid heavy shadows on every card.
- Sidebar should not cast strong shadows.
- System cards should be mostly flat.
- Tables/lists should use spacing and subtle borders, not shadows.
- Shadow means elevation, not decoration.

---

## 8. Navigation System

Navigation should answer:

Where am I?
What can I do here?
What is secondary?

Primary areas:

- Chat
- Knowledge
- Agent
- System

Rules:

- Sidebar is quiet.
- Active nav state is clear but not loud.
- TopBar shows runtime context, not marketing.
- Avoid duplicate navigation.
- Avoid drawer-heavy navigation.
- Mobile navigation should preserve orientation first, density second.

---

## 9. Workspace Design

Each workspace has one purpose.

Chat:
Ask and read.

Knowledge:
Manage documents and knowledge base state.

Agent:
Understand tool-assisted execution.

System:
Verify runtime health.

Rules:

- Do not mix workspace goals.
- Do not surface debug controls in normal reading flow.
- Do not make every workspace look like a dashboard.
- Each page should have one clear primary action.
- Secondary actions should be grouped and quieter.

---

## 10. Chat Experience

Chat is the core product.

Rules:

- Answer text must be easiest to read.
- User messages should not look like chat app bubbles if that hurts readability.
- Assistant messages should be calm, wide enough, and source-aware.
- Composer is the main control.
- Streaming should feel alive but not distracting.
- Sources should appear near the answer contextually.
- Feedback should be available but quiet.
- Mode controls should not overpower the conversation.

Chat visual priority:

1. Current answer
2. Composer
3. Active mode
4. Sources
5. Conversation list

---

## 11. Knowledge Experience

Knowledge should feel like a document workspace, not admin CRUD.

Rules:

- Show current KB clearly.
- Show document health and indexing state.
- Upload should feel safe and guided.
- Import/export are workspace operations, not primary chat actions.
- Delete requires confirmation.
- Reindex/download/delete should be row-level secondary actions.
- Avoid exposing internal paths unless useful.
- Document list should be scan-friendly.

The user should understand:

What KB am I using?
What documents are indexed?
What needs attention?
What can I safely do next?

---

## 12. Agent Experience

Agent should not look like logs.

It should read like a process:

Thinking
Planning
Calling tool
Observing result
Answering

Rules:

- Timeline over console.
- Plain-language steps over raw JSON.
- Tool arguments can be collapsible.
- Tool result should be formatted by tool type.
- Errors should explain what failed.
- Agent trace appears only in Agent mode.
- Final answer remains the destination.

Agent UI should help a normal user understand:

What did it decide?
What tool did it use?
What did it observe?
What answer did it produce?

---

## 13. Motion

Motion should clarify state.

Allowed motion:

- Message entry fade
- Streaming cursor
- Small hover transition
- Skeleton shimmer
- Collapse/expand
- Timeline progress
- Loading indicator

Rules:

- No decorative animation.
- No large bouncing.
- No slow transitions.
- Respect reduced motion.
- Motion duration should usually be 120–240ms.
- Agent running animation should feel calm, not urgent.

---

## 14. Micro Interaction

Every interaction should answer:

Did my action work?
Is something happening?
Can I undo or recover?
What changed?

Rules:

- Buttons need hover, pressed, disabled.
- Loading states must replace ambiguous silence.
- Upload needs selected file, uploading, success, error.
- Delete needs confirmation.
- Feedback needs saved state.
- Streaming needs visible activity.
- Empty states should explain next useful action.
- Error states should be human-readable.

---

## 15. Button Language

Button hierarchy:

Primary:
Only the main action in a local context.

Secondary:
Safe supporting actions.

Ghost:
Low-emphasis navigation or panel controls.

Outline:
Selectable options or filters.

Danger:
Destructive action only.

Icon button:
Only when icon meaning is obvious or has label/tooltip.

Rules:

- Do not make every button primary.
- Do not use saturated color for secondary actions.
- Button text should be verb-based.
- Destructive actions must not sit visually beside primary actions without distinction.
- Disabled buttons should explain why when possible.
- Repeated row actions should be compact and quiet.

---

## 16. Input Language

Input hierarchy:

Chat Composer:
Largest and most important input.

Search:
Compact and quiet.

Dropdown:
For bounded choices.

Textarea:
For long user expression.

Upload:
Clear file affordance.

Rules:

- Focus state must be visible.
- Placeholder should guide, not explain the whole feature.
- Chat input should support multiline naturally.
- Search input should not look like primary chat input.
- Upload area should show selected file.
- Invalid input should show inline error.

---

## 17. Status Language

Status should be consistent.

Status types:

- Healthy / ok
- Indexed / completed
- Uploaded / pending
- Running / active
- Degraded / warning
- Failed / error
- Empty / unavailable

Rules:

- Status badges are small.
- Status color is semantic.
- Do not invent a new color for every status.
- System health should be factual.
- Agent running status should be process-oriented.
- KB status should be operational.
- Chat errors should be readable and close to the failed action.

---

## 18. Brand Language

Mini ChatChat brand should feel:

- Local-first
- Evidence-driven
- Practical
- Calm
- Developer-friendly but user-facing
- Small but polished

Brand elements:

- Simple mark
- Neutral-first interface
- Reserved accent color
- Clean typography
- Source-aware chat
- Tool-aware agent timeline

Rules:

- Brand is not a gradient everywhere.
- Brand is consistency, not decoration.
- The product should feel trustworthy before it feels flashy.
- “Mini” should mean focused and readable, not incomplete.
- “ChatChat-inspired” should be visible through product structure, not copied visuals.

---

# Final Standard

Before any future UI change, ask:

1. Does this help the current user task?
2. Does this reduce or increase visual noise?
3. Is this using an existing token or inventing a one-off style?
4. Is this primary, secondary, or supporting information?
5. Would this still look professional with real user data?
6. Would this feel acceptable in a production AI SaaS product?

If the answer is unclear, simplify.