---
name: Flask Chat UX/UI Revamp
overview: Comprehensive UX/UI revamp plan for Flask + Vanilla JS + Tailwind + Vanna Components chat application, focusing on desktop experience, multiple chat sessions, and improved accessibility and visual consistency.
todos:
  - id: tailwind-tokens
    content: Update Tailwind config with token system (spacing, typography, colors, shadows)
    status: pending
  - id: spacing-refactor
    content: Refactor spacing inconsistencies across templates to use token system
    status: pending
    dependencies:
      - tailwind-tokens
  - id: accessibility-basics
    content: Add ARIA labels, aria-live regions, focus states, and skip link
    status: pending
  - id: error-handling
    content: Create error toast component and handle network/auth/API errors
    status: pending
  - id: composer-shortcuts
    content: Add keyboard shortcuts to composer (Enter, Shift+Enter, Esc)
    status: pending
  - id: app-shell
    content: Create app shell component with header and sidebar structure
    status: pending
    dependencies:
      - tailwind-tokens
  - id: session-management
    content: Implement session management (list, create, switch, delete sessions)
    status: pending
    dependencies:
      - app-shell
  - id: message-metadata
    content: Add message metadata (timestamps, copy button, regenerate)
    status: pending
    dependencies:
      - session-management
  - id: export-functionality
    content: Add export modal with JSON/Markdown/CSV format options
    status: pending
    dependencies:
      - session-management
  - id: empty-states
    content: Create empty state component with example prompts and onboarding
    status: pending
    dependencies:
      - app-shell
  - id: vanna-styling
    content: Style Vanna components using CSS variables to match design system
    status: pending
    dependencies:
      - tailwind-tokens
  - id: streaming-ux
    content: Enhance streaming UX with indicators, stop button, and smooth scrolling
    status: pending
    dependencies:
      - message-metadata
---

# Flask Chat UX/UI Revamp Plan

## Assumptions

Based on user responses and UI_DOCUMENTATION.md:

- **User Goals**: Ask questions, export/share results, admin tasks
- **Mobile**: Desktop-only (no mobile-first requirements)
- **Vanna Components**: Using `vanna-chat` web component (7.6MB React bundle, shadow DOM open mode, CSS variable theming via `--vanna-*` variables)
- **Accessibility**: Basic (focus states, labels, keyboard nav)
- **Chat History**: Multiple chat sessions needed
- **Brand**: Can define new color system (not constrained to existing Vanna colors)
- **Template System**: `backend/templates.py` processes `assets/base.html` with 48+ UI text variables
- **Backend Overrides**: Custom index route, disabled workflow handler, custom system prompt builder affect UI behavior
- **Authentication**: LDAP + Oracle DB hybrid resolver, cookies managed by `assets/js/auth.js`
- **Component Communication**: Vanna component uses SSE/WebSocket/polling, auth.js intercepts fetch/EventSource for auto-authentication

## A) Rapid UX/UI Diagnosis

### Top 10 UX Issues (Ranked by Impact)

1. **Fixed-height chat container (600px)** - `assets/base.html:102`

- **Where**: Chat container has `h-[600px]` class
- **User Harm**: Poor use of screen space, no viewport adaptation
- **Root Cause**: Hardcoded height value
- **Quick Fix**: Use `min-h-[600px] `with `flex-1` or viewport-based height
- **Deeper Fix**: Full viewport layout with proper flex/grid structure

2. **No chat session management UI**

- **Where**: Missing entirely
- **User Harm**: Cannot manage multiple conversations, no history browsing
- **Root Cause**: Single-session design
- **Quick Fix**: Add session list sidebar (hidden by default)
- **Deeper Fix**: Full session management with persistence, search, rename

3. **No loading/streaming state feedback**

- **Where**: `assets/js/chat.js` only handles `artifact-opened` events (lines 2-52), no streaming state handling
- **User Harm**: Users don't know when AI is thinking/responding
- **Root Cause**: Relies entirely on Vanna component internal states, no external state sync
- **Quick Fix**: Add wrapper loading indicator, listen to Vanna component shadow DOM changes
- **Deeper Fix**: Integrate with Vanna component custom events (if exposed) or use MutationObserver on shadowRoot

4. **No error handling UI**

- **Where**: Missing error states in templates
- **User Harm**: Failures are silent or cryptic
- **Root Cause**: No error boundary components
- **Quick Fix**: Add error toast/alert component
- **Deeper Fix**: Comprehensive error states (network, auth, API errors)

5. **Login form lacks proper validation feedback**

- **Where**: `assets/js/auth.js:50-54` - basic validation only
- **User Harm**: Unclear why login fails
- **Root Cause**: Generic error messages
- **Quick Fix**: Field-level validation with specific messages
- **Deeper Fix**: Progressive enhancement with inline validation

6. **No keyboard shortcuts documented or discoverable**

- **Where**: Missing entirely
- **User Harm**: Power users can't work efficiently
- **Root Cause**: No shortcut system implemented
- **Quick Fix**: Add basic shortcuts (Enter to send, Esc to cancel)
- **Deeper Fix**: Full shortcut system with help modal

7. **API endpoints section always visible (if enabled)**

- **Where**: `backend/templates.py:85-111` - `_build_api_endpoints_section()` always renders if `show_api_endpoints=True`
- **User Harm**: Clutters UI for non-developers
- **Root Cause**: No collapsible/conditional display, controlled only by `UI_SHOW_API_ENDPOINTS` env var
- **Quick Fix**: Add collapsible section with toggle button
- **Deeper Fix**: User preference to hide/show, or move to settings/help modal

8. **No empty state guidance**

- **Where**: Chat shows immediately after login
- **User Harm**: Users don't know what to ask
- **Root Cause**: No onboarding or suggestions
- **Quick Fix**: Add welcome message with example prompts
- **Deeper Fix**: Contextual suggestions based on user role

9. **Logout button placement unclear**

- **Where**: `assets/base.html:95` - small button in status bar
- **User Harm**: Hard to find, inconsistent with header placement
- **Root Cause**: Status bar design pattern
- **Quick Fix**: Move to header/nav area
- **Deeper Fix**: Consistent navigation pattern

10. **No export/share functionality UI**

- **Where**: Missing entirely
- **User Harm**: Cannot easily share results (SQL, charts, data)
- **Root Cause**: Feature not implemented
- **Quick Fix**: Add copy-to-clipboard for messages
- **Deeper Fix**: Full export system (CSV, SQL, images, share links)

### Top 10 UI/Visual Issues

1. **Inconsistent spacing scale** - Mixed use of `p-5`, `mb-8`, `mb-10`, `mb-4` without system
2. **Typography hierarchy unclear** - Multiple font families (serif, mono, sans) without clear roles
3. **Color usage inconsistent** - Vanna colors used directly, no semantic color system
4. **Border radius inconsistency** - `rounded-xl`, `rounded-lg` mixed without pattern
5. **Shadow usage ad-hoc** - `shadow-lg` used once, no shadow system
6. **Focus states incomplete** - Some inputs have focus rings, buttons inconsistent
7. **No hover states on interactive elements** - Buttons have hover, but links/clickable areas don't
8. **Gradient background may conflict with content** - `assets/css/styles.css:2` gradient may reduce contrast
9. **No dark mode consideration** - All colors assume light mode
10. **Component spacing drift** - Login form uses different spacing than chat container

### Accessibility Audit

**Critical Issues:**

- Missing `aria-label` on icon-only buttons
- No `aria-live` region for chat messages/streaming
- Login form lacks `aria-describedby` for error messages
- No skip-to-content link
- Missing `role="main"` on main content area
- Focus trap missing in modals (if added)
- No reduced motion support

**Moderate Issues:**

- Color contrast: Verify `text-slate-600` meets WCAG AA
- Keyboard navigation: Tab order may be illogical
- Screen reader: Chat messages need proper announcements

## B) Revamp Strategy

### Design Principles

1. **Clarity First** - Every element has a clear purpose, no visual noise
2. **Scanability** - Chat messages easy to scan, clear sender distinction
3. **Trust** - Clear citations, source visibility, error transparency
4. **Speed** - Fast perceived performance, immediate feedback
5. **Calm UI** - Subtle animations, no jarring transitions
6. **Consistency** - Unified spacing, typography, color system
7. **Accessibility** - Keyboard-first, screen reader friendly

### Information Architecture

**Current**: Single page → Login → Chat**Proposed**:

```javascript
App Shell
├── Header (logo, user menu, logout)
├── Sidebar (collapsible)
│   ├── Chat Sessions List
│   │   ├── New Chat
│   │   ├── Recent Chats (searchable)
│   │   └── Chat Actions (rename, delete, export)
│   └── Admin Panel (if admin role)
└── Main Content
    ├── Chat View (active session)
    │   ├── Chat Header (session name, actions)
    │   ├── Messages Area (scrollable)
    │   └── Composer (input, send, shortcuts)
    └── Empty State (onboarding, suggestions)
```

**Before/After Map**:

- Before: Login form → Chat (single session)
- After: Login → Session list → Active chat with history

### Component & Layout Refactor Plan

**High-Leverage Components to Standardize:**

1. **App Shell** (`_app_shell.html` partial)

- Header with logo, user info, logout
- Sidebar toggle button
- Main content wrapper
- States: default, sidebar-open, sidebar-collapsed

2. **Sidebar** (`_sidebar.html` partial)

- Session list container
- Search/filter input
- New chat button
- States: visible, hidden, collapsed

3. **Session List Item** (`_session_item.html` partial)

- Session name, preview, timestamp
- Active indicator
- Actions menu (rename, delete, export)
- States: default, active, hover, selected

4. **Chat Header** (`_chat_header.html` partial)

- Session title (editable)
- Actions (export, share, settings)
- States: default, editing

5. **Message Bubble** (wrapper for Vanna component)

- User message variant
- Assistant message variant
- Timestamp, actions (copy, regenerate)
- States: default, streaming, error, copied

6. **Composer** (`_composer.html` partial)

- Multi-line textarea
- Send button, keyboard shortcuts hint
- Character count (optional)
- States: default, typing, sending, disabled, error

7. **Loading Indicator** (`_loading.html` partial)

- Spinner variants (inline, full-page, button)
- Streaming indicator
- States: loading, streaming, idle

8. **Empty State** (`_empty_state.html` partial)

- Welcome message
- Example prompts (role-based)
- Quick actions
- States: first-run, no-sessions, no-messages

9. **Toast/Alert** (`_toast.html` partial)

- Success, error, warning, info variants
- Auto-dismiss timer
- States: showing, hiding, hidden

10. **Modal/Drawer** (`_modal.html` partial)

    - Confirmation dialogs
    - Settings panel
    - Export options
    - States: open, closing, closed

11. **Error Boundary** (`_error.html` partial)

    - Network errors
    - Auth errors
    - API errors
    - States: error, retrying, resolved

12. **Citation Card** (wrapper for Vanna citations)

    - Source display
    - Link handling
    - States: default, expanded, loading

### Visual System Refresh

**Tailwind Token Conventions** (to add to `tailwind.config`):

```javascript
// Typography Scale
fontSize: {
  'xs': ['0.75rem', { lineHeight: '1rem' }],      // 12px
  'sm': ['0.875rem', { lineHeight: '1.25rem' }], // 14px
  'base': ['1rem', { lineHeight: '1.5rem' }],    // 16px
  'lg': ['1.125rem', { lineHeight: '1.75rem' }], // 18px
  'xl': ['1.25rem', { lineHeight: '1.875rem' }],  // 20px
  '2xl': ['1.5rem', { lineHeight: '2rem' }],      // 24px
  '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
  '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
}

// Spacing Scale (consistent 4px base)
spacing: {
  '0': '0',
  '1': '0.25rem',  // 4px
  '2': '0.5rem',   // 8px
  '3': '0.75rem',  // 12px
  '4': '1rem',     // 16px
  '5': '1.25rem',  // 20px
  '6': '1.5rem',   // 24px
  '8': '2rem',     // 32px
  '10': '2.5rem',  // 40px
  '12': '3rem',    // 48px
  '16': '4rem',    // 64px
}

// Color System (semantic)
colors: {
  // Surface
  surface: {
    primary: '#ffffff',
    secondary: '#f8fafc',
    tertiary: '#f1f5f9',
    elevated: '#ffffff',
  },
  // Text
  text: {
    primary: '#0f172a',      // slate-900
    secondary: '#475569',     // slate-600
    tertiary: '#94a3b8',      // slate-400
    inverse: '#ffffff',
  },
  // Accent (primary action color)
  accent: {
    DEFAULT: '#0ea5e9',       // sky-500
    hover: '#0284c7',         // sky-600
    active: '#0369a1',        // sky-700
    light: '#e0f2fe',         // sky-100
  },
  // Semantic
  success: { ... },
  error: { ... },
  warning: { ... },
  info: { ... },
}

// Border Radius
borderRadius: {
  'none': '0',
  'sm': '0.375rem',   // 6px
  'DEFAULT': '0.5rem', // 8px
  'md': '0.625rem',   // 10px
  'lg': '0.75rem',    // 12px
  'xl': '1rem',       // 16px
  '2xl': '1.5rem',    // 24px
  'full': '9999px',
}

// Shadows
boxShadow: {
  'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  'DEFAULT': '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
  'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
}
```

**Migration Approach**: Incremental refactor

- Week 1: Update Tailwind config, fix spacing/typography in existing components
- Week 2: Extract reusable partials, standardize colors
- Week 3+: Add new features (sessions, export) using new system

## C) Chat UX Improvements

### Message Readability

**Current Issues**:

- No clear message grouping
- Timestamps missing or unclear
- Sender distinction relies on Vanna component styling

**Redesign**:

- Message groups: Group consecutive messages from same sender
- Timestamps: Show relative time (e.g., "2m ago") on hover, absolute on click
- Sender clarity: Avatar/icon + name label for assistant, user icon for user
- Line length: Max-width 65ch for message content, full-width for code blocks
- Spacing: 16px gap between message groups, 8px between messages in group

**Implementation**:

- Wrap Vanna message bubbles with metadata (timestamp, sender)
- Use CSS Grid for message layout
- Add `role="article"` with `aria-label` for each message

### Streaming Responses UX

**Current**: Relies on Vanna component internal handling**Improvements**:

- Cursor indicator: Show blinking cursor during streaming
- Partial content: Smooth scroll to bottom as content streams
- Stop button: Prominent stop button during streaming (top-right of message)
- Scroll behavior: Auto-scroll with "scroll to bottom" button if user scrolls up
- Completion indicator: Subtle animation when streaming completes

**Implementation**:

- Listen to Vanna component events for streaming state
- Add wrapper UI for streaming indicators
- Use `IntersectionObserver` for scroll-to-bottom button

### Composer UX

**Current**: Vanna component handles input internally**Enhancements**:

- Multi-line: Support Shift+Enter for new line, Enter to send
- Keyboard shortcuts: 
- `Enter` → Send
- `Shift+Enter` → New line
- `Esc` → Clear input
- `Cmd/Ctrl+K` → Focus composer
- Disabled states: Show reason (e.g., "Streaming response...")
- Error handling: Inline error message below input
- Character limit: Optional soft limit with warning

**Implementation**:

- If Vanna component exposes input, enhance with wrapper
- Otherwise, create custom composer that sends to Vanna component

### History & Navigation

**New Feature**: Session management**Components**:

- Session list sidebar:
- Search/filter sessions
- Sort by: Recent, Name, Created date
- Group by: Today, Yesterday, This Week, Older
- Session actions:
- Rename: Inline edit or modal
- Delete: Confirmation dialog
- Export: Modal with format options (JSON, Markdown, CSV)
- Duplicate: Create copy of session
- Session preview: Show last message preview, timestamp, message count

**Implementation**:

- Store sessions in `localStorage` or backend API (if available)
- Create session management JS module
- Add sidebar component with session list

### Trust & Safety Cues

**Improvements**:

- Citations: Prominent display of sources, expandable details
- System status: Connection indicator (online/offline)
- Error messages: Human-readable, actionable
- Confidence indicators: Show when AI is uncertain (if available from API)

**Implementation**:

- Enhance Vanna citation display with wrapper
- Add status bar component
- Create error message component with retry actions

### Empty States

**First-run**:

- Welcome message with app purpose
- Example prompts based on user role (admin vs user)
- Quick start guide (optional)

**No sessions**:

- "Start a new conversation" CTA
- Example prompts

**No messages in session**:

- Contextual suggestions
- Recent queries from other sessions (if applicable)

### Mobile Behavior

**Note**: Desktop-only per requirements, but ensure basic responsiveness**Minimum**:

- Sidebar becomes drawer on smaller screens
- Composer stays sticky at bottom
- Messages stack vertically
- Touch targets: Minimum 44x44px

## D) Vanna Components Integration Plan

**Current Integration** (per UI_DOCUMENTATION.md):

- `<vanna-chat>` component: 7.6MB React bundle in `assets/js/vanna-components.js`
- Shadow DOM: Open mode (`mode: "open"`), accessible via `element.shadowRoot`
- CSS Variables: Extensive `--vanna-*` variable system (colors, spacing, typography, shadows, z-index)
- Component Architecture: ChatHeader, MessageList, InputBox with internal TextComponent, CodeComponent, DataFrameComponent, PlotlyComponent
- Communication: SSE (`/api/vanna/v2/chat_sse`), WebSocket (`/api/vanna/v2/chat_websocket`), Polling (`/api/vanna/v2/chat_poll`)
- Authentication: Auto-injected via `auth.js` fetch/EventSource interceptors

**Existing Vanna CSS Variables** (from vanna-components.js):

```css
/* Colors */
--vanna-navy: rgb(2, 61, 96);
--vanna-cream: rgb(231, 225, 207);
--vanna-teal: rgb(21, 168, 168);
--vanna-orange: rgb(254, 93, 38);
--vanna-magenta: rgb(191, 19, 99);

/* Backgrounds */
--vanna-background-root: rgb(255, 255, 255);
--vanna-background-default: rgb(231, 225, 207);
--vanna-background-higher: rgb(244, 246, 248);
--vanna-foreground-default: rgb(2, 61, 96);
--vanna-foreground-dimmer: rgb(71, 85, 105);

/* Accents */
--vanna-accent-primary-default: rgb(21, 168, 168);
--vanna-accent-primary-hover: rgb(21, 168, 168);

/* Spacing */
--vanna-space-0 through --vanna-space-16 (0px to 64px)

/* Border Radius */
--vanna-border-radius-sm: 6px;
--vanna-border-radius-md: 10px;
--vanna-border-radius-lg: 14px;

/* Chat-specific */
--vanna-chat-bubble-radius: 18px;
--vanna-chat-spacing: 16px;
--vanna-chat-avatar-size: 40px;
```

**Styling Strategy**:

1. **CSS Variables Override** (primary method):

- Override Vanna CSS variables in `assets/css/styles.css` or inline styles
- Map our Tailwind token system to Vanna variables
- Example:
   ```css
      vanna-chat {
        --vanna-accent-primary-default: #0ea5e9; /* sky-500 */
        --vanna-foreground-default: #0f172a;     /* slate-900 */
        --vanna-background-root: #ffffff;
        --vanna-chat-spacing: 1rem;               /* 16px */
        --vanna-border-radius-lg: 0.75rem;       /* 12px */
      }
   ```




2. **Wrapper Patterns**:

- Wrap `<vanna-chat>` in container div with our styling
- Add metadata (timestamps, actions) outside shadow DOM using CSS Grid/Flexbox
- Access shadow DOM via `document.querySelector('vanna-chat').shadowRoot` for advanced manipulation

3. **Event Handling**:

- Known events: `artifact-opened` (handled in `chat.js:5`)
- Listen for custom events on `vanna-chat` element
- Use `MutationObserver` on `shadowRoot` for DOM changes (last resort)
- Access internal elements: `shadowRoot.querySelector('.chat-messages')`, `shadowRoot.querySelector('.message-input')`

4. **Component Access Points** (from vanna-components.js analysis):

- Message input: `shadowRoot.querySelector('textarea.message-input, input.message-input')`
- Progress tracker: `shadowRoot.querySelector('vanna-progress-tracker')`
- Status bar: `shadowRoot.querySelector('vanna-status-bar')`
- Messages container: `shadowRoot.querySelector('.chat-messages')`
- Rich components: `shadowRoot.querySelector('.rich-components-container')`

**Component Mapping**:

- `vanna-chat` → Our chat container wrapper (add header, metadata)
- Internal message bubbles → Wrap with our message metadata (timestamp, copy button)
- Internal composer → Enhance with keyboard shortcuts wrapper (if input accessible)
- Internal progress tracker → Sync with our loading indicators

**Accessibility**:

- Vanna component uses shadow DOM - ARIA labels may be encapsulated
- Add our own ARIA regions outside shadow DOM for announcements
- Test with screen readers (shadow DOM can affect screen reader behavior)
- Ensure focus management works across shadow boundary

**Lifecycle**:

- Initialize: Vanna component auto-initializes when DOM loads
- Re-renders: Component handles internal updates, we sync external state
- Session changes: May need to re-initialize or clear component state
- Cleanup: Remove event listeners, clear MutationObservers on unmount

**Integration with Backend**:

- Backend override: `backend/main.py:111-118` custom index route affects initial render
- System prompt: `UserAwareSystemPromptBuilder` affects LLM responses (not UI directly)
- Workflow handler: Disabled (`workflow_handler=None`) - no "Admin View" messages

## E) Screen-by-Screen Proposal

### 1. App Shell Layout

**Before Problems**:

- No consistent header
- Logout button in status bar (unclear)
- No navigation structure

**After Layout**:

```javascript
┌─────────────────────────────────────────────────┐
│ Header                                          │
│ [Logo] [App Name]        [User Menu] [Logout]  │
├──────────┬──────────────────────────────────────┤
│ Sidebar  │ Main Content                         │
│ [Toggle] │                                      │
│          │                                      │
│ Sessions │ Chat View                           │
│ List     │                                      │
│          │                                      │
│          │                                      │
└──────────┴──────────────────────────────────────┘
```

**Interaction Rules**:

- Sidebar toggle: Click hamburger to show/hide
- User menu: Dropdown with profile, settings, logout
- Responsive: Sidebar becomes drawer on <1024px

**Microcopy**:

- Header: "Database Chat" or configurable
- User menu: "Signed in as {username}"

**Edge Cases**:

- No sessions: Show empty state in sidebar
- Loading: Skeleton loaders for session list

**Accessibility**:

- `role="banner"` on header
- `role="navigation"` on sidebar
- `role="main"` on main content
- Skip link: "Skip to main content"

**Engineering**:

- Create `assets/partials/_app_shell.html` partial (new directory)
- Header component with user menu dropdown (use existing `loggedInUser` from `auth.js`)
- Sidebar component with toggle state (vanilla JS state management)
- Use Tailwind `lg:` breakpoint for sidebar behavior
- Integrate with existing `auth.js` cookie system (`vanna_user`, `vanna_groups`)
- Consider backend template system: extend `backend/templates.py` to support partials

### 2. Main Chat Screen

**Before Problems**:

- Fixed 600px height
- No header for active session
- No message metadata

**After Layout**:

```javascript
┌─────────────────────────────────────┐
│ Chat Header                         │
│ [Session Name] [Export] [Settings]  │
├─────────────────────────────────────┤
│                                     │
│ Messages Area (scrollable)          │
│                                     │
│ [User Message]                      │
│ [Assistant Message]                 │
│ [Citations]                         │
│                                     │
├─────────────────────────────────────┤
│ Composer                            │
│ [Input] [Send] [Shortcuts]          │
└─────────────────────────────────────┘
```

**Interaction Rules**:

- Session name: Click to edit inline
- Export: Dropdown with format options
- Messages: Auto-scroll on new message, manual scroll pauses auto-scroll
- Composer: Focus on load, Enter to send

**Microcopy**:

- Empty: "Start a conversation by asking a question..."
- Streaming: "Thinking..." or "Generating response..."
- Error: "Failed to send message. [Retry]"

**Edge Cases**:

- Long messages: Expandable with "Show more"
- Code blocks: Copy button, syntax highlighting
- Tables: Horizontal scroll, export button

**Accessibility**:

- `aria-live="polite"` for new messages
- `aria-live="assertive"` for errors
- `aria-label` on action buttons
- Keyboard: Tab through messages, focus composer

**Engineering**:

- Use flexbox for layout (header, messages, composer)
- Messages area: `flex-1` with `overflow-y-auto`
- Composer: Sticky at bottom
- Integrate with Vanna component: Access `shadowRoot` for message list, listen to `artifact-opened` events (extend `chat.js`)
- Fix fixed height: Change `h-[600px] `in `assets/base.html:102` to viewport-based height
- Wrap `<vanna-chat>` with metadata containers outside shadow DOM

### 3. Empty Chat State

**Before Problems**:

- No guidance, just empty chat

**After Layout**:

```javascript
┌─────────────────────────────────────┐
│                                     │
│   [Icon/Illustration]               │
│                                     │
│   Welcome to Database Chat          │
│                                     │
│   Get started by asking:            │
│   • "Show me sales data"            │
│   • "What tables are available?"    │
│   • "Generate a report for Q4"     │
│                                     │
│   [Start New Chat]                  │
│                                     │
└─────────────────────────────────────┘
```

**Interaction Rules**:

- Click example prompts to fill composer
- "Start New Chat" creates new session

**Microcopy**:

- Title: "Welcome! Let's get started"
- Examples: Role-based (admin sees schema examples, user sees query examples)

**Edge Cases**:

- First-time user: Show onboarding tooltips
- Returning user: Show recent sessions instead

**Engineering**:

- Create `assets/partials/_empty_state.html` partial
- Example prompts: Use role-based prompts (admin vs user) from `config.ui.text` or new config
- Click handler: Access Vanna component input via `shadowRoot.querySelector('.message-input')` and populate
- Integration: Show when `vanna-chat` has no messages (check `shadowRoot.querySelector('.chat-messages')` children)

### 4. Error/Offline State

**Before Problems**:

- Errors are silent or generic

**After Layout**:

```javascript
┌─────────────────────────────────────┐
│ [Error Icon]                        │
│                                     │
│ Connection Error                    │
│                                     │
│ Unable to connect to the server.    │
│ Please check your connection.       │
│                                     │
│ [Retry] [Go Offline]                │
└─────────────────────────────────────┘
```

**Interaction Rules**:

- Retry: Attempts reconnection
- Go Offline: Shows cached messages (if available)

**Microcopy**:

- Network error: "Connection lost. Retrying..."
- Auth error: "Session expired. Please log in again."
- API error: "Something went wrong. [Retry] or [Report Issue]"

**Edge Cases**:

- Partial failure: Show which messages failed
- Rate limit: Show cooldown timer

**Engineering**:

- Create `_error.html` partial
- Error types: network, auth, API, validation
- Retry logic with exponential backoff

### 5. Settings/Help (if exists)

**Proposed Layout**:

- Modal or drawer
- Sections: Preferences, Keyboard Shortcuts, About
- Preferences: Theme (if dark mode added), notifications, auto-save

## F) Implementation Plan

### Two-Track Rollout

**Week 1-2: Quick Wins**

1. **Visual Consistency** (S)

- Update Tailwind config in `assets/base.html:10-27` with token system
- Fix spacing inconsistencies (use spacing scale)
- Standardize border radius, shadows
- Map Tailwind tokens to Vanna CSS variables in `assets/css/styles.css`
- **Files**: `assets/base.html` (inline config), `assets/css/styles.css`, `backend/templates.py`

2. **Spacing Refactor** (S)

- Replace ad-hoc spacing with scale
- Use consistent gaps/paddings
- **Files**: `assets/base.html`, `assets/css/styles.css`

3. **Accessibility Basics** (M)

- Add ARIA labels to buttons
- Add `aria-live` regions
- Fix focus states
- Add skip link
- **Files**: `assets/base.html`, `assets/js/auth.js`, `assets/js/chat.js`

4. **Composer Polish** (M)

- Add keyboard shortcuts (Enter, Shift+Enter, Esc)
- Improve disabled states
- Add error handling
- Access Vanna input: `document.querySelector('vanna-chat').shadowRoot.querySelector('.message-input')`
- Listen to input events and intercept keyboard shortcuts
- **Files**: `assets/js/chat.js` (extend existing artifact handler), new `assets/js/composer.js`

5. **Error Handling** (M)

- Add error toast component
- Handle network errors
- Handle auth errors
- **Files**: New `_toast.html`, `assets/js/error-handler.js`

**Week 3+: Deeper Refactor**

6. **Component Extraction** (L)

- Create Jinja partials for reusable components
- Extract app shell, sidebar, message wrapper
- **Files**: New `assets/partials/` directory

7. **Session Management** (L)

- Add session list sidebar
- Implement session CRUD (localStorage initially, backend API if available)
- Add session search/filter
- Store session metadata: name, timestamp, message count, last message preview
- Integrate with Vanna component: May need to re-initialize or clear on session switch
- **Files**: New `assets/js/sessions.js`, `assets/partials/_sidebar.html`, `assets/partials/_session_item.html`
- **Backend**: Consider adding session API endpoints if persistence needed

8. **Chat History UX** (L)

- Add message metadata (timestamps, actions)
- Implement message grouping
- Add copy/regenerate actions
- Access Vanna messages: `shadowRoot.querySelector('.chat-messages')` children
- Wrap messages with metadata containers (outside shadow DOM)
- Use MutationObserver to detect new messages in shadow DOM
- **Files**: New `assets/js/messages.js`, `assets/partials/_message.html` (wrapper)

9. **Export/Share** (M)

- Add export modal
- Implement export formats (JSON, Markdown, CSV)
- Add share functionality (if backend supports)
- **Files**: `_export_modal.html`, `assets/js/export.js`

10. **Empty States** (S)

    - Create empty state component
    - Add example prompts (role-based: admin sees schema examples, user sees query examples)
    - Add onboarding (optional)
    - Check Vanna component state: `shadowRoot.querySelector('#empty-state')` or message count
    - **Files**: `assets/partials/_empty_state.html`, new `assets/js/onboarding.js`
    - **Integration**: Use `config.ui.text` for customizable prompts or extend with new UI variables

### Prioritized Backlog

| Item | User Value | Effort | Risk | Dependencies | Acceptance Criteria ||------|------------|--------|------|--------------|-------------------|| Tailwind token system | High | S | Low | None | Consistent spacing/colors across app || Accessibility basics | High | M | Low | None | WCAG AA compliance, keyboard nav works || Error handling | High | M | Medium | Toast component | All errors show user-friendly messages || Composer shortcuts | Medium | S | Low | None | Enter sends, Shift+Enter newline || Session management | High | L | High | Backend API (if needed) | Can create, list, switch sessions || Message metadata | Medium | M | Low | Session management | Timestamps, copy button on messages || Export functionality | Medium | M | Medium | Session management | Can export session as JSON/Markdown || Empty states | Low | S | Low | None | Shows guidance when no messages || Visual consistency | Medium | S | Low | Token system | All components use design system || Sidebar navigation | Medium | M | Medium | Session management | Sidebar shows sessions, can toggle |

### QA Checklist

**Visual Regression**:

- [ ] Login form matches design
- [ ] Chat layout matches design
- [ ] Spacing consistent across screens
- [ ] Colors match token system
- [ ] Typography hierarchy correct

**Keyboard-Only Flows**:

- [ ] Can navigate entire app with keyboard
- [ ] Focus indicators visible
- [ ] Tab order logical
- [ ] All interactive elements keyboard accessible
- [ ] Modals/drawers have focus trap

**Screen Reader**:

- [ ] All buttons have labels
- [ ] Form fields have labels/descriptions
- [ ] Chat messages announced
- [ ] Errors announced
- [ ] Landmarks present (header, nav, main)

**Mobile Testing** (basic responsiveness):

- [ ] Layout works on tablet (768px)
- [ ] Sidebar becomes drawer
- [ ] Touch targets adequate
- [ ] No horizontal scroll

**Streaming Behavior**:

- [ ] Streaming indicator shows
- [ ] Auto-scroll works
- [ ] Stop button functional
- [ ] Completion animation smooth

## G) Concrete Assets

### Updated Sitemap

**Current**: Single route `/` handled by `backend/main.py:111-118` custom index**Proposed** (client-side routing):

```javascript
/ (index)
├── Login (if not authenticated) - handled by auth.js
└── Chat (if authenticated)
    ├── /#session=default (default session, localStorage)
    ├── /#session=:sessionId (specific session, localStorage)
    └── /#session=new (new session, localStorage)
```

**Note**: Backend doesn't need route changes - all client-side via hash routing or localStorage state management. Backend routes remain:

- `GET /` → Custom index (login or chat)
- `POST /api/vanna/v2/auth_test` → Authentication
- `POST /api/vanna/v2/chat_sse` → Chat streaming
- `GET /assets/<path>` → Static files

### Component Inventory

**Components with States** (see Component Refactor Plan section for details)

### Tailwind Token Conventions

See "Visual System Refresh" section above for full token list.**Key Conventions**:

- Spacing: 4px base unit (0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16)
- Typography: 7-step scale (xs to 4xl)
- Colors: Semantic naming (surface, text, accent, success, error, warning, info)
- Border radius: 6-step scale (none, sm, DEFAULT, md, lg, xl, 2xl, full)
- Shadows: 5-step scale (sm, DEFAULT, md, lg, xl)

### Minimal Example Snippets

**Jinja Partial Structure** (Note: Current system uses string replacement, not Jinja):Current: `backend/templates.py` uses string replacement (`{{PLACEHOLDER}}`)**Option 1**: Extend template system to support partials:

```python
# backend/templates.py
def _load_partial(filename: str) -> str:
    assets_dir = Path(__file__).parent.parent / "assets" / "partials"
    file_path = assets_dir / filename
    if file_path.exists():
        return file_path.read_text(encoding='utf-8')
    return ""

# In get_ldap_login_html():
app_shell = _load_partial("_app_shell.html")
# Replace {{APP_SHELL}} in base.html
```

**Option 2**: Keep string replacement, create partial files for organization:

```html
<!-- assets/partials/_app_shell.html -->
<header role="banner" class="...">
  {{HEADER_CONTENT}}
</header>
<div class="flex h-screen">
  <aside role="navigation" class="...">
    {{SIDEBAR_CONTENT}}
  </aside>
  <main role="main" class="flex-1">
    {{MAIN_CONTENT}}
  </main>
</div>
```

**Vanilla JS Module Pattern** (`assets/js/sessions.js`):

```javascript
const SessionManager = (() => {
  const storageKey = 'chat_sessions';
  
  const getSessions = () => {
    const stored = localStorage.getItem(storageKey);
    return stored ? JSON.parse(stored) : [];
  };
  
  const saveSession = (session) => {
    const sessions = getSessions();
    sessions.push(session);
    localStorage.setItem(storageKey, JSON.stringify(sessions));
  };
  
  return { getSessions, saveSession };
})();
```

**Tailwind Class Patterns**:

- Container: `max-w-7xl mx-auto px-4`
- Card: `bg-surface-elevated rounded-lg shadow-md p-6`
- Button primary: `bg-accent text-white px-4 py-2 rounded-md hover:bg-accent-hover focus:ring-2 focus:ring-accent`
- Input: `border border-outline-default rounded-md px-3 py-2 focus:ring-2 focus:ring-accent focus:border-accent`

---

## Additional Considerations from UI_DOCUMENTATION.md

### Backend UI Overrides to Preserve

1. **Custom Index Route** (`backend/main.py:111-118`):

- Must preserve login-first flow
- Custom index calls `get_ldap_login_html()` from `templates.py`
- Do not break template variable replacement system

2. **Workflow Handler Disabled** (`backend/main.py:552`):

- `workflow_handler=None` - no "Admin View" messages
- Keep this behavior for cleaner UI

3. **System Prompt Builder** (`backend/system_prompt_builder.py`):

- Affects LLM responses, not UI directly
- But user-aware prompts improve UX - preserve

4. **Custom Auth Endpoint** (`backend/main.py:125-166`):

- `/api/vanna/v2/auth_test` used by `auth.js`
- Must continue working for login flow

5. **Assets Route** (`backend/main.py:80-100`):

- Serves `/assets/<path>` with path traversal protection
- Must work for new partials directory

### Template System Integration

- Current: `backend/templates.py` loads files and replaces `{{PLACEHOLDER}}` strings
- 48+ UI text variables via `config.ui.text` (UITextConfig)
- All customizable via `UI_*` environment variables
- Extend system to support:
- Partial loading (`_load_partial()` function)
- Nested replacements (partials can have their own placeholders)
- Conditional rendering (if `show_api_endpoints`)

### Vanna Component Limitations

- Shadow DOM encapsulation: Cannot directly style internal elements
- CSS variables: Primary theming method (must use `--vanna-*` overrides)
- Event system: Limited known events (`artifact-opened`), may need MutationObserver
- Input access: Can access via `shadowRoot.querySelector('.message-input')` but may break on updates
- Message access: Can read but cannot modify internal message structure

### File Structure Updates Needed

```javascript
assets/
├── base.html (modify)
├── css/
│   ├── google-fonts.css (keep)
│   └── styles.css (extend with Vanna variable overrides)
├── js/
│   ├── auth.js (extend)
│   ├── chat.js (extend)
│   ├── tailwindcss.js (keep)
│   ├── vanna-components.js (keep, don't modify)
│   ├── sessions.js (new)
│   ├── messages.js (new)
│   ├── composer.js (new)
│   ├── error-handler.js (new)
│   └── onboarding.js (new)
└── partials/ (new directory)
    ├── _app_shell.html
    ├── _header.html
    ├── _sidebar.html
    ├── _session_item.html
    ├── _chat_header.html
    ├── _message.html
    ├── _composer.html
    ├── _loading.html
    ├── _empty_state.html
    ├── _toast.html
    ├── _modal.html
    └── _error.html
```



### Environment Variables to Add

Extend `backend/config.py` UITextConfig with:

- `empty_state_title`
- `empty_state_description`
- `example_prompts_admin` (JSON array)
- `example_prompts_user` (JSON array)
- `session_default_name`
- `export_formats` (JSON array)