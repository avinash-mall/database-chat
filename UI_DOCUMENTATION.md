
# Vanna Chatbot UI / Frontend Documentation

> **📌 Comprehensive Self-Sufficient Guide**  
> This document contains all details needed to rebuild and understand the complete UI/frontend of the Vanna Oracle Database Chat application, including frontend architecture, backend communication, authentication flows, security modules, configuration options, and all available tools.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Frontend File Structure & Components](#2-frontend-file-structure--components)
3. [Configuration System](#3-configuration-system)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Communication Protocols & APIs](#5-communication-protocols--apis)
6. [Row-Level Security (RLS) System](#6-row-level-security-rls-system)
7. [Admin Tools & Slash Commands](#7-admin-tools--slash-commands)
8. [Schema Training & Memory Management](#8-schema-training--memory-management)
9. [UI Customization & Text Configuration](#9-ui-customization--text-configuration)
10. [Deployment & Rebuilding Guide](#10-deployment--rebuilding-guide)
11. [Workflow Diagrams](#11-workflow-diagrams)

---

## 1. System Architecture Overview

### High-Level Architecture

The application follows a **client-server architecture** with these key components:

-   **Frontend**: Custom HTML/JS interface using the `<vanna-chat>` Web Component
-   **Backend**: Python Flask server acting as API gateway and orchestrator
-   **Authentication**: Hybrid LDAP + Oracle Database role resolution
-   **Security**: Row-Level Security (RLS) for data access control
-   **LLM**: Ollama or OpenAI for natural language processing
-   **Vector Database**: Milvus for agent memory and schema storage

### Component Interaction Diagram

```mermaid
graph TB
    subgraph "Browser (Client)"
        UI[HTML/CSS/JS UI]
        Auth[auth.js Authentication]
        Chat[vanna-chat Component]
    end
    
    subgraph "Flask Server (Backend)"
        Routes[Flask Routes]
        Resolver[HybridUserResolver]
        Agent[Vanna Agent]
        Tools[Tool Registry]
        RLS[RLS Service]
        Prompt[System Prompt Builder]
    end
    
    subgraph "External Services"
        LDAP[LDAP Server]
        Oracle[(Oracle Database)]
        Milvus[(Milvus Vector DB)]
        LLM[Ollama/OpenAI]
    end
    
    UI --> Auth
    Auth --> Routes
    UI --> Chat
    Chat --> Routes
    
    Routes --> Resolver
    Routes --> Agent
    Resolver --> LDAP
    Resolver --> Oracle
    
    Agent --> Tools
    Agent --> Prompt
    Agent --> LLM
    Agent --> Milvus
    
    Tools --> RLS
    RLS --> Oracle
    Prompt --> RLS
    
    style UI fill:#e1f5ff
    style Chat fill:#e1f5ff
    style Agent fill:#fff4e6
    style RLS fill:#ffe7e7
    style Oracle fill:#e8f5e9
```

---

## 2. Frontend File Structure & Components

### Directory Layout

```
assets/
├── base.html                 # Main HTML template
├── css/
│   ├── google-fonts.css      # Font definitions
│   └── styles.css            # Custom CSS overrides
└── js/
    ├── auth.js               # Authentication logic (139 lines)
    ├── tailwindcss.js        # TailwindCSS library
    └── vanna-components.js   # Chat Web Component (7.6MB)
```

### Component Breakdown

### Component Breakdown

#### A. base.html (127 lines)

The main HTML template with template variable placeholders:

**Key Sections**:
1. **Head Section**:
   - TailwindCSS configuration with custom color palette
   - Font loading (Space Grotesk, Roboto Slab, Space Mono)
   - Dynamic styles injection via `{{STYLES}}`
   - Web component script loading

2. **Header Section**:
   - Configurable title, subtitle, and description
   - Template variables: `{{HEADER_TITLE}}`, `{{HEADER_SUBTITLE}}`, `{{HEADER_DESCRIPTION}}`

3. **Login Container** (`loginContainer`):
   - Username input (`usernameInput`)
   - Password input (`passwordInput`)
   - Submit button with loading state
   - Error message display (`loginError`, `errorMessage`)
   - LDAP authentication note

4. **Logged-In Status Display** (`loggedInStatus`):
   - Hidden by default, shown after login
   - Displays current username
   - Logout button

5  **Chat Container** (`chatSections`):
   - Hidden by default, shown after authentication
   - Embeds `<vanna-chat>` component
   - Optional API endpoints section (configurable)

**Custom TailwindCSS Color Palette**:
```javascript
colors: {
    'vanna-navy': '#023d60',
    'vanna-cream': '#e7e1cf',
    'vanna-teal': '#15a8a8',
    'vanna-orange': '#fe5d26',
    'vanna-magenta': '#bf1363',
}
```

---

### Detailed File Documentation

#### 1. **base.html** - Main HTML Template (127 lines)

**Location**: `assets/base.html`  
**Size**: 5,516 bytes  
**Purpose**: The primary HTML template that serves as the skeleton for the entire UI

**Template Variable System**:

This file uses a template replacement system where placeholders like `{{VARIABLE}}` are replaced by `templates.py` during server-side rendering.

**Complete Template Variables** (71 total):

| Section | Variables | Purpose |
|---------|-----------|---------|
| **Meta** | `{{PAGE_TITLE}}` | Browser tab title |
| **Styles** | `{{STYLES}}`, `{{COMPONENT_SCRIPT}}` | CSS injection and component loading |
| **Header** | `{{HEADER_TITLE}}`, `{{HEADER_SUBTITLE}}`, `{{HEADER_DESCRIPTION}}` | Page header content |
| **Dev Mode** | `{{DEV_MODE_MESSAGE}}` | Development mode notification |
| **Login Form** | `{{LOGIN_TITLE}}`, `{{LOGIN_DESCRIPTION}}`, `{{LOGIN_FAILED_LABEL}}` | Login UI text |
| **Form Fields** | `{{USERNAME_LABEL}}`, `{{USERNAME_PLACEHOLDER}}`, `{{PASSWORD_LABEL}}`, `{{PASSWORD_PLACEHOLDER}}`, `{{LOGIN_BUTTON}}` | Input field labels/placeholders |
| **Auth Note** | `{{LDAP_AUTH_NOTE}}` | LDAP authentication info |
| **Session** | `{{LOGGED_IN_PREFIX}}`, `{{LOGOUT_BUTTON}}` | Logged-in state UI |
| **Chat** | `{{CHAT_TITLE}}`, `{{API_BASE_URL}}` | Chat component configuration |
| **API Section** | `{{API_ENDPOINTS_SECTION}}` | Optional API documentation section |
| **Scripts** | `{{AUTH_JS}}`, `{{CHAT_JS}}` | JavaScript injection |

**Key DOM Elements**:

```html
<!-- Login Form (lines 45-89) -->
<div id="loginContainer">
  <form id="loginForm">
    <input id="usernameInput" type="text" autocomplete="username" />
    <input id="passwordInput" type="password" autocomplete="current-password" />
    <button id="loginButton" type="submit">
      <span id="loginButtonText">Login</span>
    </button>
  </form>
  <div id="loginError" class="hidden">
    <span id="errorMessage"></span>
  </div>
</div>

<!-- Logged-In Status (lines 92-98) -->
<div id="loggedInStatus" class="hidden">
  <span id="loggedInUser"></span>
  <button id="logoutButton">Logout</button>
</div>

<!-- Chat Interface (lines 101-114) -->
<div id="chatSections" class="hidden">
  <vanna-chat 
    title="{{CHAT_TITLE}}"
    api-base="{{API_BASE_URL}}"
    sse-endpoint="/api/vanna/v2/chat_sse"
    ws-endpoint="/api/vanna/v2/chat_websocket"
    poll-endpoint="/api/vanna/v2/chat_poll">
  </vanna-chat>
</div>
```

**TailwindCSS Configuration** (lines 10-27):
```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'vanna-navy': '#023d60',    // Primary dark color
                'vanna-cream': '#e7e1cf',   // Background accent
                'vanna-teal': '#15a8a8',    // Primary brand color
                'vanna-orange': '#fe5d26',  // Accent color
                'vanna-magenta': '#bf1363', // Accent color
            },
            fontFamily: {
                'sans': ['Space Grotesk', 'ui-sans-serif', 'system-ui'],
                'serif': ['Roboto Slab', 'ui-serif', 'Georgia'],
                'mono': ['Space Mono', 'ui-monospace', 'monospace'],
            }
        }
    }
}
```

**Connections**:
- **Loaded by**: Flask route `/` in `main.py`
- **Processed by**: `templates.py::get_ldap_login_html()`
- **Loads**: `google-fonts.css`, `styles.css`, `tailwindcss.js`, `vanna-components.js`, `auth.js`
- **Interacts with**: `auth.js` for DOM manipulation

---

#### 2. **auth.js** - Authentication Logic (139 lines)

**Location**: `assets/js/auth.js`  
**Size**: 5,582 bytes  
**Purpose**: Client-side authentication, session management, and automatic request interception

**Code Structure**:

##### a. Cookie Utilities (lines 1-15)

```javascript
// Retrieve cookie value
const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    return parts.length === 2 ? parts.pop().split(';').shift() : null;
};

// Set cookie with 365-day expiration
const setCookie = (name, value) => {
    const expires = new Date(Date.now() + 365 * 864e5).toUTCString();
    document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
};

// Delete cookie
const deleteCookie = (name) => {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
};
```

**Cookies Managed**:
- `vanna_user`: Username (e.g., "alice")
- `vanna_groups`: Comma-separated group list (e.g., "admin,superuser")
- `vanna_auth`: Base64-encoded credentials for session persistence

##### b. DOMContentLoaded Event Handler (lines 18-107)

**Element References**:
```javascript
const loginForm = document.getElementById('loginForm');
const loginButton = document.getElementById('loginButton');
const loginButtonText = document.getElementById('loginButtonText');
const loginError = document.getElementById('loginError');
const errorMessage = document.getElementById('errorMessage');
const loginContainer = document.getElementById('loginContainer');
const loggedInStatus = document.getElementById('loggedInStatus');
const chatSections = document.getElementById('chatSections');
const loggedInUser = document.getElementById('loggedInUser');
const logoutButton = document.getElementById('logoutButton');
```

**Auto-Login Check** (lines 34-41):
```javascript
const savedUser = getCookie('vanna_user');
if (savedUser) {
    loginContainer.classList.add('hidden');
    loggedInStatus.classList.remove('hidden');
    chatSections.classList.remove('hidden');
    loggedInUser.textContent = savedUser;
}
```
*Purpose*: On page load, check if user already has session cookies. If yes, skip login and go straight to chat.

**Login Form Handler** (lines 43-92):
```javascript
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('usernameInput').value.trim();
    const password = document.getElementById('passwordInput').value;
    
    // Validation
    if (!username || !password) {
        loginError.classList.remove('hidden');
        errorMessage.textContent = '{{LOGIN_ERROR_MISSING_FIELDS}}';
        return;
    }

    // Show loading state
    loginButton.disabled = true;
    loginButtonText.innerHTML = '<span class="loading-spinner"></span>{{AUTHENTICATING_TEXT}}';
    loginError.classList.add('hidden');

    try {
        // Encode credentials to Base64
        const credentials = btoa(`${username}:${password}`);
        
        // Send authentication request
        const response = await fetch('/api/vanna/v2/auth_test', {
            method: 'POST',
            headers: {
                'Authorization': `Basic ${credentials}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ test: true })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Store session in cookies
            setCookie('vanna_user', username);
            setCookie('vanna_groups', data.groups ? data.groups.join(',') : 'user');
            setCookie('vanna_auth', credentials);
            
            // Update UI
            loginContainer.classList.add('hidden');
            loggedInStatus.classList.remove('hidden');
            chatSections.classList.remove('hidden');
            loggedInUser.textContent = username;
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || '{{LOGIN_ERROR_INVALID_CREDENTIALS}}');
        }
    } catch (error) {
        loginError.classList.remove('hidden');
        errorMessage.textContent = error.message || '{{LOGIN_ERROR_INVALID_CREDENTIALS}}';
    } finally {
        loginButton.disabled = false;
        loginButtonText.textContent = '{{LOGIN_BUTTON}}';
    }
});
```

**Logout Handler** (lines 94-106):
```javascript
if (logoutButton) {
    logoutButton.addEventListener('click', () => {
        deleteCookie('vanna_user');
        deleteCookie('vanna_groups');
        deleteCookie('vanna_auth');
        
        loginContainer.classList.remove('hidden');
        loggedInStatus.classList.add('hidden');
        chatSections.classList.add('hidden');
        
        document.getElementById('usernameInput').value = '';
        document.getElementById('passwordInput').value = '';
    });
}
```

##### c. Global Request Interception (lines 109-138)

**Fetch Interceptor** (lines 109-124):
```javascript
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const authToken = getCookie('vanna_auth');
    if (authToken) {
        if (args[1]) {
            args[1].headers = args[1].headers || {};
            if (!args[1].headers['Authorization']) {
                args[1].headers['Authorization'] = `Basic ${authToken}`;
            }
        } else {
            args[1] = { headers: { 'Authorization': `Basic ${authToken}` } };
        }
    }
    return originalFetch.apply(this, args);
};
```
*Purpose*: Automatically inject `Authorization` header into ALL fetch requests made by the application (including those from vanna-chat component).

**EventSource Interceptor** (lines 126-138):
```javascript
const originalEventSource = window.EventSource;
window.EventSource = function(url, eventSourceInitDict) {
    const authToken = getCookie('vanna_auth');
    if (authToken) {
        eventSourceInitDict = eventSourceInitDict || {};
        eventSourceInitDict.headers = eventSourceInitDict.headers || {};
        if (!eventSourceInitDict.headers['Authorization']) {
            eventSourceInitDict.headers['Authorization'] = `Basic ${authToken}`;
        }
    }
    return new originalEventSource(url, eventSourceInitDict);
};
```
*Purpose*: Inject authentication headers into Server-Sent Events (SSE) connections for streaming LLM responses.

**Connections**:
- **Loaded by**: `base.html` via `{{AUTH_JS}}` template variable
- **Depends on**: DOM elements in `base.html`, `styles.css` for `.loading-spinner`
- **Interacts with**: Backend `/api/vanna/v2/auth_test` endpoint
- **Modifies**: Global `window.fetch` and `window.EventSource`

---

#### 3. **styles.css** - Custom Styling (27 lines)

**Location**: `assets/css/styles.css`  
**Size**: 525 bytes  
**Purpose**: Application-wide custom CSS overrides and animations

**Complete Code**:

```css
/* Global background gradient */
body {
    background: linear-gradient(to bottom, #e7e1cf, #ffffff);
    min-height: 100vh;
}

/* Ensure vanna-chat component fills container */
vanna-chat {
    width: 100%;
    height: 100%;
    display: block;
}

/* Loading spinner for authentication button */
.loading-spinner {
    border: 3px solid #e7e1cf;        /* Light border */
    border-top: 3px solid #15a8a8;    /* Teal accent */
    border-radius: 50%;
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 8px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
```

**Usage Breakdown**:

1. **Body Gradient** (lines 1-4):
   - Creates subtle cream-to-white gradient background
   - Uses `vanna-cream` color (#e7e1cf)
   - Ensures full viewport height

2. **vanna-chat Sizing** (lines 6-10):
   - Forces Web Component to fill parent container
   - Required for proper chat display in `chatSections` div

3. **Loading Spinner** (lines 12-26):
   - Animated circular spinner
   - Used by `auth.js` during login (line 57: `loginButtonText.innerHTML`)
   - Color scheme matches brand (cream/teal)
   - CSS class: `.loading-spinner`

**Connections**:
- **Loaded by**: `templates.py` via `_load_template_file('styles.css')`
- **Injected into**: `base.html` via `{{STYLES}}` placeholder
- **Used by**: `auth.js` (loading spinner), `base.html` (body/vanna-chat)

---

#### 4. **google-fonts.css** - Font Definitions (78 lines)

**Location**: `assets/css/google-fonts.css`  
**Size**: 2,228 bytes  
**Purpose**: Self-hosted Google Fonts for offline/LAN deployment

**Font Families Defined**:

| Font Family | Weights Included | Purpose | Lines |
|-------------|------------------|---------|-------|
| **Roboto Slab** | 400, 500, 600, 700 | Serif font for headers | 1-28 |
| **Space Grotesk** | 300, 400, 500, 600, 700 | Sans-serif for body text | 29-63 |
| **Space Mono** | 400, 700 | Monospace for code | 64-78 |

**Font File Mapping**:

```css
/* Roboto Slab (Headers, Titles) */
@font-face {
  font-family: 'Roboto Slab';
  font-weight: 400;  /* Regular */
  src: url(../fonts/BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjojISWaA.ttf);
}
@font-face {
  font-family: 'Roboto Slab';
  font-weight: 700;  /* Bold */
  src: url(../fonts/BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjoa4OWaA.ttf);
}

/* Space Grotesk (Body Text) */
@font-face {
  font-family: 'Space Grotesk';
  font-weight: 400;  /* Regular */
  src: url(../fonts/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7oUUsj.ttf);
}

/* Space Mono (Code, Monospace) */
@font-face {
  font-family: 'Space Mono';
  font-weight: 400;  /* Regular */
  src: url(../fonts/i7dPIFZifjKcF5UAWdDRUEY.ttf);
}
```

**Font File Details** (11 files in `assets/fonts/`):

| File | Font | Weight | Size |
|------|------|--------|------|
| `BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjojISWaA.ttf` | Roboto Slab | 400 | 101 KB |
| `BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjovoSWaA.ttf` | Roboto Slab | 500 | 102 KB |
| `BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjoUoOWaA.ttf` | Roboto Slab | 600 | 102 KB |
| `BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjoa4OWaA.ttf` | Roboto Slab | 700 | 102 KB |
| `V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj62UUsj.ttf` | Space Grotesk | 300 | 69 KB |
| `V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7oUUsj.ttf` | Space Grotesk | 400 | 69 KB |
| `V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7aUUsj.ttf` | Space Grotesk | 500 | 69 KB |
| `V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj42Vksj.ttf` | Space Grotesk | 600 | 69 KB |
| `V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj4PVksj.ttf` | Space Grotesk | 700 | 69 KB |
| `i7dPIFZifjKcF5UAWdDRUEY.ttf` | Space Mono | 400 | 81 KB |
| `i7dMIFZifjKcF5UAWdDRaPpZYFI.ttf` | Space Mono | 700 | 79 KB |

**Actual UI Usage** (from TailwindCSS config in `base.html`):

```javascript
fontFamily: {
    'sans': ['Space Grotesk', 'ui-sans-serif', 'system-ui'],
    'serif': ['Roboto Slab', 'ui-serif', 'Georgia'],
    'mono': ['Space Mono', 'ui-monospace', 'monospace'],
}
```

Applied via Tailwind classes:
- `font-serif` → Headers (`<h1>`, `<h2>`) use **Roboto Slab**
- `font-sans` → Default body text uses **Space Grotesk**
- `font-mono` → Code/technical text uses **Space Mono**

**Why Self-Hosted?**
- **Offline capability**: Works in air-gapped/LAN environments
- **Performance**: No external CDN dependency
- **Privacy**: No Google Fonts tracking
- **Reliability**: No external service downtime

**Connections**:
- **Loaded by**: `base.html` line 7: `<link href="/assets/css/google-fonts.css" rel="stylesheet">`
- **Depends on**: 11 font files in `assets/fonts/` directory
- **Used by**: All text throughout the application

---

#### 5. **tailwindcss.js** - TailwindCSS Library

**Location**: `assets/js/tailwindcss.js`  
**Size**: 407,362 bytes (~398 KB)  
**Purpose**: Full TailwindCSS library for browser-side CSS generation

**What is it?**
- **Standalone TailwindCSS**: Complete CSS framework that runs in the browser
- **Just-in-Time (JIT) compilation**: Generates CSS classes on-the-fly as they're used
- **No build step required**: Perfect for rapid development and template-based apps

**How it works**:
1. Script scans the DOM for Tailwind class names (e.g., `bg-vanna-teal`, `rounded-lg`)
2. Generates corresponding CSS rules dynamically
3. Injects styles into the page's `<head>`

**Configuration** (defined in `base.html` lines 10-27):
```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'vanna-navy': '#023d60',
                'vanna-cream': '#e7e1cf',
                'vanna-teal': '#15a8a8',
                'vanna-orange': '#fe5d26',
                'vanna-magenta': '#bf1363',
            },
            fontFamily: {
                'sans': ['Space Grotesk', ...],
                'serif': ['Roboto Slab', ...],
                'mono': ['Space Mono', ...],
            }
        }
    }
}
```

**Example Usage in `base.html`**:
```html
<!-- Custom color classes -->
<h1 class="text-4xl font-bold text-vanna-navy mb-2 font-serif">

<!-- Background and border -->
<div class="bg-white p-8 rounded-xl shadow-lg border border-vanna-teal/30">

<!-- Button styling -->
<button class="w-full px-4 py-3 bg-vanna-teal text-white rounded-lg hover:bg-vanna-navy">
```

**Classes Used in Application**:
- **Colors**: `text-vanna-navy`, `bg-vanna-teal`, `border-vanna-cream`
- **Spacing**: `p-5`, `mb-8`, `mx-auto`, `space-y-2`
- **Layout**: `max-w-6xl`, `flex`, `grid`, `hidden`
- **Typography**: `text-4xl`, `font-bold`, `font-serif`
- **Effects**: `shadow-lg`, `rounded-lg`, `hover:bg-vanna-navy`

**Connections**:
- **Loaded by**: `base.html` line 8: `<script src="/assets/js/tailwindcss.js"></script>`
- **Configured by**: `base.html` lines 10-27 (inline `<script>` with `tailwind.config`)
- **Used by**: All HTML elements with Tailwind classes in `base.html`

**Note**: In production, you would typically use a build process to generate a static CSS file, but the standalone version is perfect for this template-based Flask app.

---

#### 6. **vanna-components.js** - Chat Web Component

**Location**: `assets/js/vanna-components.js`  
**Size**: 7,607,051 bytes (~7.6 MB)  
**Purpose**: Pre-built React/Web Component providing the complete chat interface

**What is it?**
- **Bundled React Application**: Compiled from React source code into a single JS file
- **Custom Web Component**: Registered as `<vanna-chat>` HTML element
- **Self-contained**: All dependencies bundled (React, ReactDOM, UI components)

**Component Architecture**:

```
<vanna-chat>
  ├── ChatHeader
  │   └── Title, Status Indicator
  ├── MessageList
  │   ├── UserMessage (text bubble)
  │   ├── AssistantMessage
  │   │   ├── TextComponent (Markdown renderer)
  │   │   ├── CodeComponent (SQL highlighting)
  │   │   ├── DataFrameComponent (table display)
  │   │   └── PlotlyComponent (charts)
  │   └── LoadingIndicator
  └── InputBox
      ├── TextArea (auto-resize)
      └── SendButton
```

**Usage in HTML** (from `base.html` lines 103-110):
```html
<vanna-chat
    title="{{CHAT_TITLE}}"
    api-base="{{API_BASE_URL}}"
    sse-endpoint="/api/vanna/v2/chat_sse"
    ws-endpoint="/api/vanna/v2/chat_websocket"
    poll-endpoint="/api/vanna/v2/chat_poll"
    style="width: 100%; height: 100%; display: block;">
</vanna-chat>
```

**Component Attributes**:

| Attribute | Purpose | Example Value |
|-----------|---------|---------------|
| `title` | Chat window header | "Oracle Database AI Chat" |
| `api-base` | Base URL for API calls | "" (same origin) |
| `sse-endpoint` | Server-Sent Events URL | "/api/vanna/v2/chat_sse" |
| `ws-endpoint` | WebSocket URL | "/api/vanna/v2/chat_websocket" |
| `poll-endpoint` | Polling fallback URL | "/api/vanna/v2/chat_poll" |

**Communication Protocol**:

1. **User sends message**: Input box captures text
2. **Component chooses transport**:
   - **Primary**: Server-Sent Events (SSE) for streaming
   - **Fallback**: WebSocket for bi-directional
   - **Legacy**: HTTP polling
3. **Backend streams response**: LLM thoughts, SQL, results
4. **Component renders**:
   - Text → Markdown
   - SQL → Syntax highlighted code block
   - DataFrame → HTML table
   - Plotly JSON → Interactive chart

**Authentication Integration**:
- Component uses standard `fetch()` and `EventSource()`
- `auth.js` intercepts these calls and injects `Authorization` header
- Seamless authentication without component modification

**Rendering Capabilities**:

```javascript
// Text/Markdown
<TextComponent content="Here's your query result..." />

// SQL Code
<CodeComponent 
    code="SELECT * FROM employees WHERE department_id = 30"
    language="sql" />

// Data Table
<DataFrameComponent 
    data={[
        {name: "Alice", salary: 50000},
        {name: "Bob", salary: 60000}
    ]}
    columns={["name", "salary"]} />

// Plotly Chart
<PlotlyComponent 
    data={plotlyJSON}
    layout={{title: "Sales by Quarter"}} />
```

**Connections**:
- **Loaded by**: `base.html` via `{{COMPONENT_SCRIPT}}` placeholder
- **Source**: `templates.py` line 39: `<script type="module" src="/assets/js/vanna-components.js"></script>`
- **Depends on**: `auth.js` for authentication
- **Communicates with**: Flask backend endpoints (`/api/vanna/v2/*`)

---

### File Dependency Graph

```mermaid
graph TD
    Flask[Flask Server main.py] -->|Serves| BaseHTML[base.html]
    Templates[templates.py] -->|Processes| BaseHTML
    
    BaseHTML -->|Loads| GoogleFonts[google-fonts.css]
    BaseHTML -->|Loads| Styles[styles.css]
    BaseHTML -->|Loads| Tailwind[tailwindcss.js]
    BaseHTML -->|Loads| VannaComp[vanna-components.js]
    BaseHTML -->|Injects| AuthJS[auth.js]
    
    GoogleFonts -->|References| Fonts[fonts/*.ttf - 11 files]
    
    Tailwind -->|Configured by| BaseHTML
    
    AuthJS -->|Manipulates| BaseHTML
    AuthJS -->|Intercepts| VannaComp
    AuthJS -->|Uses| Styles
    
    VannaComp -->|Makes requests to| Flask
    
    BaseHTML -->|Uses classes from| Tailwind
    BaseHTML -->|Styled by| Styles
    BaseHTML -->|Fonts from| GoogleFonts
    
    style BaseHTML fill:#e1f5ff
    style AuthJS fill:#fff4e6
    style VannaComp fill:#ffe7e7
    style Flask fill:#e8f5e9
```

### Assets Folder Complete Structure

```
assets/
├── base.html                 # 127 lines, 5.5 KB - Main template
├── css/
│   ├── google-fonts.css      # 78 lines, 2.2 KB - Self-hosted fonts
│   └── styles.css            # 27 lines, 525 B - Custom CSS
├── fonts/
│   ├── BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjojISWaA.ttf  # Roboto Slab 400
│   ├── BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjovoSWaA.ttf  # Roboto Slab 500
│   ├── BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjoUoOWaA.ttf  # Roboto Slab 600
│   ├── BngbUXZYTXPIvIBgJJSb6s3BzlRRfKOFbvjoa4OWaA.ttf  # Roboto Slab 700
│   ├── V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj62UUsj.ttf # Space Grotesk 300
│   ├── V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7oUUsj.ttf # Space Grotesk 400
│   ├── V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7aUUsj.ttf # Space Grotesk 500
│   ├── V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj42Vksj.ttf # Space Grotesk 600
│   ├── V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj4PVksj.ttf # Space Grotesk 700
│   ├── i7dPIFZifjKcF5UAWdDRUEY.ttf                      # Space Mono 400
│   └── i7dMIFZifjKcF5UAWdDRaPpZYFI.ttf                  # Space Mono 700
└── js/
    ├── auth.js               # 139 lines, 5.5 KB - Authentication
    ├── tailwindcss.js        # ~398 KB - CSS framework
    └── vanna-components.js   # ~7.6 MB - Chat component

Total: 17 files, ~8 MB
```

---

#### B. auth.js (139 lines)

**Core Functionality**:

1. **Cookie Management** (lines 2-15):
   ```javascript
   getCookie(name)        // Retrieve cookie value
   setCookie(name, value) // Set cookie with 365-day expiration
   deleteCookie(name)     // Delete cookie
   ```

2. **Auto-Login Check** (lines 34-41):
   - On page load, checks for `vanna_user` cookie
   - If found, hides login and shows chat immediately

3. **Login Form Handler** (lines 43-92):
   - Validates username/password fields
   - Encodes credentials to Base64
   - POSTs to `/api/vanna/v2/auth_test`
   - On success: stores cookies (`vanna_user`, `vanna_groups`, `vanna_auth`)
   - On failure: displays error message

4. **Logout Handler** (lines 94-106):
   - Deletes all auth cookies
   - Resets UI to login state

5. **Request Interception** (lines 109-138):
   - **Fetch Interceptor**: Patches `window.fetch` to auto-inject `Authorization` header
   - **EventSource Interceptor**: Patches `window.EventSource` for SSE authentication

**Key Variables Used**:
- Template replacements: `{{LOGIN_ERROR_MISSING_FIELDS}}`, `{{LOGIN_ERROR_INVALID_CREDENTIALS}}`, `{{AUTHENTICATING_TEXT}}`, `{{LOGIN_BUTTON}}`

#### C. vanna-components.js (7.6MB)

Pre-built React/Web Component bundle providing:
- Chat window with message history
- Input box with send button
- Message rendering:
  - Text (Markdown support)
  - SQL code blocks (syntax highlighted)
  - Data tables (from Pandas DataFrames)
  - Plotly charts (interactive)
- Streaming response handling
- Error display

---

## 3. Configuration System

### Configuration Files

1. **`backend/config.py`** (420 lines): Central configuration management
2. **`.env`**: Environment variables (not committed to git)

### Configuration Classes

#### A. OracleConfig
```python
user: str              # Database username
password: str          # Database password
dsn: str              # Connection string (host:port/sid)
schema_name: str      # Schema to search (defaults to user)
```

**Environment Variables**:
- `ORACLE_USER` (required)
- `ORACLE_PASSWORD` (required)
- `ORACLE_DSN` (required)
- `ORACLE_SCHEMA` (optional)

#### B. LdapConfig
```python
host: str                     # LDAP server hostname
port: int                     # LDAP port (389 or 636)
base_dn: str                  # Base DN for searches
user_dn_template: str         # Template for user DN (e.g., "uid={username},ou=users,dc=example,dc=com")
admin_group_dn: str           # Admin group DN
bind_dn: str                  # Service account DN
bind_password: str            # Service account password
use_ssl: bool = False         # Enable LDAPS
email_domain: str = "vanna.ai"
guest_username: str = "guest"
guest_email: str             # Guest user email
```

**Environment Variables**:
- `LDAP_HOST` (required)
- `LDAP_PORT` (required)
- `LDAP_BASE_DN` (required)
- `LDAP_USER_DN_TEMPLATE` (required)
- `LDAP_ADMIN_GROUP_DN` (required)
- `LDAP_BIND_DN` (required)
- `LDAP_BIND_PASSWORD` (required)
- `LDAP_USE_SSL` (optional, default: false)
- `EMAIL_DOMAIN` (optional, default: vanna.ai)

#### C. UITextConfig (48 configurable text strings!)

Complete list of customizable UI text:

| Variable | Default Value | Usage |
|----------|---------------|-------|
| `page_title` | "Agents Chat" | Browser tab title |
| `header_title` | "Agents" | Main header text |
| `header_subtitle` | "DATA-FIRST AGENTS" | Subtitle below header |
| `header_description` | "Interactive AI Assistant..." | Description text |
| `login_title` | "Login to Continue" | Login form title |
| `login_description` | "Enter your credentials..." | Login form description |
| `login_failed_label` | "Login Failed:" | Error prefix |
| `username_label` | "Username" | Username field label |
| `username_placeholder` | "Enter your username" | Username placeholder |
| `password_label` | "Password" | Password field label |
| `password_placeholder` | "Enter your password" | Password placeholder |
| `login_button` | "Login" | Login button text |
| `authenticating_text` | "Authenticating..." | Loading state text |
| `ldap_auth_note` | "LDAP Authentication: Use..." | Info note below form |
| `logged_in_prefix` | "Logged in as" | Status text prefix |
| `logout_button` | "Logout" | Logout button text |
| `chat_title` | "Oracle Database AI Chat" | Chat window title |
| `api_endpoints_title` | "API Endpoints" | API section title |
| `api_sse_description` | "Server-Sent Events streaming" | SSE endpoint description |
| `api_ws_description` | "WebSocket real-time chat" | WebSocket description |
| `api_poll_description` | "Request/response polling" | Polling description |
| `api_health_description` | "Health check" | Health endpoint description |
| ... and more | | |

**All UI text can be customized via `UI_*` environment variables** (e.g., `UI_PAGE_TITLE`, `UI_LOGIN_BUTTON`)

#### D. RLSConfig
```python
enabled: bool = True             # Enable/disable RLS
cache_ttl: float = 300.0         # Cache duration (seconds)
excluded_tables: str = ""        # Comma-separated list of excluded tables
```

**Environment Variables**:
- `RLS_ENABLED` (optional, default: true)
- `RLS_CACHE_TTL` (optional, default: 300)
- `RLS_EXCLUDED_TABLES` (optional, comma-separated)

#### E. UIConfig
```python
show_api_endpoints: bool = True  # Show/hide API endpoints section
text: UITextConfig               # All UI text customizations
```

**Environment Variables**:
- `UI_SHOW_API_ENDPOINTS` (optional, default: true)
- All `UI_*` variables (see UITextConfig)

#### F. MilvusConfig, ServerConfig, AgentConfig
See `config.py` lines 142-319 for complete details.

---

## 4. Authentication & Authorization

### Authentication Flow Architecture

```mermaid
graph LR
    A[User Enters Credentials] --> B[auth.js]
    B --> C[Base64 Encode]
    C --> D[POST /auth_test]
    D --> E[HybridUserResolver]
    E --> F[LDAP Bind Test]
    F --> G{Valid?}
    G -->|No| H[401 Error]
    G -->|Yes| I[Query AI_USERS Table]
    I --> J{User Exists?}
    J -->|No| K[Access Denied]
    J -->|Yes| L[Extract Roles]
    L --> M[Return User Object]
    M --> N[Set Cookies]
    N --> O[Show Chat UI]
```

### HybridUserResolver (main.py lines 180-393)

**Purpose**: Combines LDAP authentication with database role management.

**Process**:
1. **Authenticate against LDAP**:
   - Binds using `user_dn_template.format(username=username)`
   - Validates password
   - Retrieves user attributes (email, uid)

2. **Query Oracle AI_USERS table**:
   ```sql
   SELECT IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER 
   FROM AI_USERS 
   WHERE UPPER(USERNAME) = UPPER(:username)
   ```

3. **Map flags to groups**:
   - `IS_ADMIN = 1` → `'admin'`
   - `IS_SUPERUSER = 1` → `'superuser'`
   - `IS_NORMALUSER = 1` → `'user'`

4. **Return User object**:
   ```python
   User(
       id=username,
       email=email,
       username=username,
       group_memberships=['admin', 'superuser', 'user']
   )
   ```

**Important**: User MUST exist in both LDAP and AI_USERS table to log in.

### AI_USERS Table Structure

**Standard Columns**:
- `USERNAME` VARCHAR2(50) - Primary key
- `IS_ADMIN` NUMBER(1) - Admin flag
- `IS_SUPERUSER` NUMBER(1) - Superuser flag
- `IS_NORMALUSER` NUMBER(1) - Normal user flag

**Dynamic Filter Columns** (for RLS):
Any additional columns beyond the standard ones become RLS filter columns (e.g., `EMPLOYEE_ID`, `DEPARTMENT_ID`, `REGION_ID`)

---

## 5. Communication Protocols & APIs

### API Endpoints

#### A. Authentication Endpoint

**POST** `/api/vanna/v2/auth_test`

**Request**:
```http
POST /api/vanna/v2/auth_test HTTP/1.1
Authorization: Basic YXZpbmFzaDphdmluYXNoMTIz
Content-Type: application/json

{"test": true}
```

**Success Response (200)**:
```json
{
    "success": true,
    "user": "avinash",
    "email": "avinash@example.com",
    "groups": ["admin", "superuser", "user"],
    "is_admin": true
}
```

**Error Response (401)**:
```json
{
    "error": "LDAP authentication failed for user 'avinash'"
}
```

**Implementation**: `main.py` lines 121-166

#### B. Chat Endpoints

**Server-Sent Events (SSE)**: `/api/vanna/v2/chat_sse`
- Streaming responses from LLM
- Authentication via `Authorization` header (auto-injected by auth.js)

**WebSocket**: `/api/vanna/v2/chat_websocket`
- Real-time bidirectional chat
- Authentication via handshake

**Polling**: `/api/vanna/v2/chat_poll`
- Request/response polling (fallback)

**All registered by**: `vanna.servers.flask.routes.register_chat_routes()`

#### C. Static Assets

**GET** `/assets/<path:filepath>`
- Serves files from `assets/` directory
- Security: Path traversal protection (lines 84-96 in main.py)
- Serves: HTML, CSS, JS, fonts

#### D. Health Check

**GET** `/health`
```json
{
    "status": "healthy",
    "service": "vanna"
}
```

### Request/Response Flow

```mermaid
sequenceDiagram
    participant Browser
    participant auth.js
    participant Flask
    participant Agent
    participant LLM
    participant Oracle
    
    Browser->>auth.js: User sends "Show sales for Q1"
    auth.js->>auth.js: Get vanna_auth cookie
    auth.js->>Flask: POST /chat_sse (Authorization header)
    Flask->>Flask: Resolve user (HybridUserResolver)
    Flask->>Agent: Execute query with user context
    Agent->>Agent: Build system prompt (w/ RLS filters)
    Agent->>LLM: Send prompt
    LLM-->>Agent: Return tool call (run_sql)
    Agent->>Oracle: Execute SQL with RLS filtering
    Oracle-->>Agent: Return filtered results
    Agent-->>Flask: Stream results
    Flask-->>Browser: SSE stream (SQL, DataFrame, Chart)
    Browser->>Browser: Render results in chat
```

---

## 6. Row-Level Security (RLS) System

### Overview

The RLS system (`rls_service.py`, 516 lines) dynamically filters SQL query results based on user attributes.

### Key Concepts

1. **Filter Columns**: Automatically discovered from AI_USERS table
   - Any column NOT in `{USERNAME, IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER}`
   - Examples: `EMPLOYEE_ID`, `DEPARTMENT_ID`, `REGION_ID`, `EMAIL`, `PERSON_ID`

2. **User Filter Values**: Retrieved from AI_USERS for each user
   - Example: User 'john' has `DEPARTMENT_ID = 10`, `REGION_ID = 'US'`

3. **SQL Modification**: Automatic WHERE clause injection
   - Original: `SELECT * FROM employees`
   - Modified: `SELECT * FROM employees WHERE employees.DEPARTMENT_ID = :rls_param_0`

### RLS Workflow

```mermaid
graph TD
    A[SQL Query Generated] --> B{RLS Enabled?}
    B -->|No| C[Execute Original SQL]
    B -->|Yes| D{User Privileged?}
    D -->|Admin/Superuser| C
    D -->|Normal User| E[Get User Filter Values]
    E --> F[Parse SQL Table Names]
    F --> G[Find Matching Filter Columns]
    G --> H[Build WHERE Conditions]
    H --> I[Inject WHERE Clause]
    I --> J[Execute Filtered SQL]
```

### RowLevelSecurityService Class

**Methods**:

| Method | Purpose | Lines |
|--------|---------|-------|
| `get_filter_columns()` | Discover filter columns from AI_USERS | 94-143 |
| `get_user_filter_values(username)` | Get user's filter values | 145-202 |
| `get_table_columns(table_name)` | Get table schema | 204-251 |
| `apply_rls_filters(sql, user_values)` | Modify SQL with WHERE clause | 341-428 |
| `_inject_where_clause(sql, condition)` | Insert WHERE/AND into SQL | 430-501 |
| `_extract_table_names(parsed_sql)` | Parse table names from SQL | 253-325 |

**Caching**:
- Filter columns cached for 5 minutes (TTL configurable)
- Table schema cached per table
- User filter values cached per user
- Cache cleared via `clear_cache()` or `clear_user_cache(username)`

**Excluded Tables**:
- Configure via `RLS_EXCLUDED_TABLES` environment variable
- Example: `RLS_EXCLUDED_TABLES=LOOKUP_TABLES,REFERENCE_DATA`
- Tables in this list bypass RLS filtering

### Example RLS Application

**User**: `alice`
**AI_USERS Row**:
```
USERNAME: alice
DEPARTMENT_ID: 30
REGION_ID: WEST
```

**Original SQL**:
```sql
SELECT employee_name, salary 
FROM employees 
ORDER BY salary DESC
```

**Modified SQL**:
```sql
SELECT employee_name, salary 
FROM employees 
WHERE (employees.DEPARTMENT_ID = :rls_param_0 AND employees.REGION_ID = :rls_param_1) 
ORDER BY salary DESC
```

**Bind Parameters**:
```python
{
    'rls_param_0': 30,
    'rls_param_1': 'WEST'
}
```

---

## 7. Admin Tools & Slash Commands

### Tool Registry & Access Control

Tools are registered with specific access groups (main.py lines 496-526):

```python
tools = ToolRegistry()
tools.register_local_tool(db_tool, access_groups=['admin', 'superuser', 'user'])
tools.register_local_tool(GatherSchemaTool(...), access_groups=['admin', 'superuser'])
tools.register_local_tool(CleanupMemoryTool(...), access_groups=['admin', 'superuser'])
tools.register_local_tool(ListAllTablesTool(...), access_groups=['admin', 'superuser', 'user'])
```

### Available Tools

#### 1. SecureRunSqlTool (secure_sql_tool.py)

**Name**: `run_sql`  
**Access**: `admin`, `superuser`, `user`  
**Purpose**: Execute SQL queries with automatic RLS filtering  

**Behavior**:
- **Privileged Users** (admin/superuser): Execute SQL without modification
- **Normal Users**: Apply RLS filters via `RowLevelSecurityService`

**UI Invocation**: Automatically called when LLM generates SQL

#### 2. GatherSchemaTool (gather_schema_tool.py, 70 lines)

**Slash Command**: `/gather`  
**Access**: `admin`, `superuser`  
**Purpose**: Manually trigger schema training  

**Process**:
1. Call `SchemaTrainer.train_schema()`
2. Query Oracle metadata (tables, columns, relationships)
3. Generate DDL-like documentation
4. Optionally generate LLM-based table descriptions
5. Store in Milvus vector database

**UI Response**:
```
Schema training completed successfully. 
Trained 15 database objects. 
The schema information is now available in agent memory.
```

**Error Handling**: Returns user-friendly error if unauthorized or DB error occurs

#### 3. CleanupMemoryTool (cleanup_memory_tool.py, 80 lines)

**Slash Command**: `/cleanup`  
**Access**: `admin`, `superuser`  
**Purpose**: Clear all stored memories from Milvus  

**Args**:
```python
confirm: bool  # Must be True to proceed
```

**Process**:
1. Connect to Milvus
2. Drop collection `vanna_memory`
3. Return success message

**UI Response**:
```
Successfully cleared all memories by dropping collection 'vanna_memory'. 
You can now run /gather to re-train the agent.
```

**Safety**: Requires explicit confirmation parameter

#### 4. ListAllTablesTool (discover_tables_tool.py, 305 lines)

**Slash Command**: `/discover`  
**Access**: `admin`, `superuser`, `user`  
**Purpose**: List all accessible database tables/views  

**Args**:
```python
include_columns: bool = True      # Include column names
table_filter: Optional[str] = None  # Filter by table name
```

**Process**:
1. Query `USER_TAB_COLUMNS` metadata view
2. Group by table name
3. Optionally filter by pattern
4. Exclude system tables (AI_USERS, PLAN_TABLE, etc.)

**UI Response**:
```markdown
📊 **Database Schema Overview**

Found 12 tables matching your criteria:

### EMPLOYEES
- Type: TABLE
- Columns (7): EMPLOYEE_ID, FIRST_NAME, LAST_NAME, EMAIL, PHONE_NUMBER, HIRE_DATE, SALARY

### DEPARTMENTS
- Type: TABLE  
- Columns (3): DEPARTMENT_ID, DEPARTMENT_NAME, MANAGER_ID

...
```

#### 5. SaveTextMemoryTool, SearchSavedCorrectToolUsesTool

**Access**: Various  
**Purpose**: Agent memory operations  
**Auto-invoked**: By the Agent during query processing

---

## 8. Schema Training & Memory Management

### SchemaTrainer Class (schema_trainer.py, 637 lines)

**Purpose**: Load Oracle database schema into Vanna's agent memory for LLM context.

#### Key Methods

| Method | Purpose | Lines |
|--------|---------|-------|
| `get_schema_info()` | Query Oracle metadata | 63-200 |
| `generate_ddl(table_info)` | Create DDL-like documentation | 202-256 |
| `generate_relationship_summary(schema_info)` | Document foreign key relationships | 258-291 |
| `generate_table_documentation(table_info)` | LLM-based table descriptions | 380-519 |
| `train_schema()` | Full training pipeline | 521-592 |
| `get_schema_summary()` | Concise schema overview | 594-631 |

#### Training Pipeline (`train_schema()`)

1. **Metadata Query**:
   ```sql
   SELECT 
       t.TABLE_NAME, 
       t.TABLE_TYPE,
       c.COLUMN_NAME,
       c.DATA_TYPE,
       c.DATA_LENGTH,
       c.NULLABLE,
       c.COMMENTS
   FROM USER_TABLES t
   JOIN USER_TAB_COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
   WHERE t.TABLE_NAME NOT IN ('AI_USERS', 'PLAN_TABLE', ...)
   ORDER BY t.TABLE_NAME, c.COLUMN_ID
   ```

2. **DDL Generation** (per table):
   ```sql
   CREATE TABLE EMPLOYEES (
       EMPLOYEE_ID NUMBER(6) NOT NULL,
       FIRST_NAME VARCHAR2(20),
       LAST_NAME VARCHAR2(25) NOT NULL,
       EMAIL VARCHAR2(25) NOT NULL UNIQUE,
       HIRE_DATE DATE NOT NULL,
       SALARY NUMBER(8,2)
   );
   ```

3. **LLM Documentation** (optional):
   - Sample first 20 rows from table
   - Send to LLM with prompt: "Analyze this table and describe its purpose..."
   - LLM returns human-readable description

4. **Milvus Storage**:
   - Each table's DDL + documentation stored as separate memory item
   - Semantic search enabled for retrieval during query generation

#### Excluded Tables

```python
EXCLUDED_TABLES = {
    'AI_USERS',        # Privacy - user identity table
    'CHAINED_ROWS',    # Oracle system table
    'PLAN_TABLE',      # Oracle explain plan table
    'MVIEW$_ADV_WORKLOAD',
    'MVIEW$_ADV_LOG',
}
```

---

## 9. UI Customization & Text Configuration

### Template System (templates.py, 112 lines)

**Function**: `get_ldap_login_html(api_base_url, show_api_endpoints, ui_text)`

**Process**:
1. Load template files:
   - `base.html`
   - `styles.css`
   - `auth.js`
   - `chat.js` (minimal initialization for vanna-chat component)

2. Replace placeholders:
   ```python
   replacements = {
       '{{PAGE_TITLE}}': ui_text.page_title,
       '{{HEADER_TITLE}}': ui_text.header_title,
       '{{LOGIN_BUTTON}}': ui_text.login_button,
       '{{API_BASE_URL}}': api_base_url,
       '{{STYLES}}': styles_css,
       '{{AUTH_JS}}': auth_js,
       # ... 70+ replacements total
   }
   ```

3. Return complete HTML

### Customization Examples

**Example 1**: Rebrand the application
```bash
# .env file
UI_PAGE_TITLE=Acme Corp Data Assistant
UI_HEADER_TITLE=Acme Data Intelligence
UI_HEADER_SUBTITLE=POWERED BY AI
UI_CHAT_TITLE=Ask Acme Anything
```

**Example 2**: Multilingual support (Spanish)
```bash
UI_USERNAME_LABEL=Usuario
UI_PASSWORD_LABEL=Contraseña
UI_LOGIN_BUTTON=Iniciar Sesión
UI_LOGIN_FAILED_LABEL=Error de autenticación:
UI_LOGOUT_BUTTON=Cerrar Sesión
```

**Example 3**: Hide API endpoints
```bash
UI_SHOW_API_ENDPOINTS=false
```

---

## 10. Deployment & Rebuilding Guide

### Minimum Required Files

To rebuild the UI from scratch:

```
project/
├── backend/
│   ├── config.py           # Configuration management
│   ├── main.py             # Flask server + HybridUserResolver
│   ├── templates.py        # HTML template generation
│   ├── rls_service.py      # Row-level security
│   ├── secure_sql_tool.py  # Secure SQL execution
│   ├── system_prompt_builder.py  # User-aware prompts
│   ├── schema_trainer.py   # Schema training
│   ├── gather_schema_tool.py     # /gather command
│   ├── cleanup_memory_tool.py    # /cleanup command
│   └── discover_tables_tool.py   # /discover command
├── assets/
│   ├── base.html
│   ├── css/
│   │   ├── google-fonts.css
│   │   └── styles.css
│   └── js/
│       ├── auth.js
│       ├── tailwindcss.js
│       └── vanna-components.js
├── .env                     # Environment configuration
└── requirements.txt
```

### Step-by-Step Rebuild

#### 1. Set Up Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
# Oracle Database
ORACLE_USER=hr
ORACLE_PASSWORD=password
ORACLE_DSN=localhost:1521/XEPDB1

# LDAP
LDAP_HOST=ldap
LDAP_PORT=1389
LDAP_BASE_DN=dc=example,dc=com
LDAP_USER_DN_TEMPLATE=uid={username},ou=users,dc=example,dc=com
LDAP_ADMIN_GROUP_DN=cn=admins,ou=groups,dc=example,dc=com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=adminpassword

# Server
VANNA_HOST=0.0.0.0
VANNA_PORT=8000

# LLM (Ollama example)
INFERENCE_PROVIDER=ollama
OLLAMA_MODEL=llama3
OLLAMA_HOST=http://localhost:11434

# Milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_COLLECTION=vanna_memory

# UI Customization (optional)
UI_PAGE_TITLE=My Custom Chat
UI_SHOW_API_ENDPOINTS=true
EOF
```

#### 2. Frontend Assets

**Copy or create**:
- `assets/base.html` (from this project)
- `assets/js/auth.js` (from this project)
- `assets/css/styles.css` (from this project)
- Download `vanna-components.js` from Vanna repository

**TailwindCSS**: Include via CDN in base.html:
```html
<script src="/assets/js/tailwindcss.js"></script>
```

#### 3. Oracle Setup

```sql
-- Create identity table
CREATE TABLE AI_USERS (
    USERNAME VARCHAR2(50) PRIMARY KEY,
    IS_ADMIN NUMBER(1) DEFAULT 0,
    IS_SUPERUSER NUMBER(1) DEFAULT 0,
    IS_NORMALUSER NUMBER(1) DEFAULT 1,
    -- RLS filter columns (optional)
    EMPLOYEE_ID NUMBER(6),
    DEPARTMENT_ID NUMBER(4),
    REGION_ID VARCHAR2(10)
);

-- Add users
INSERT INTO AI_USERS VALUES ('admin', 1, 1, 1, NULL, NULL, NULL);
INSERT INTO AI_USERS VALUES ('alice', 0, 0, 1, 100, 30, 'WEST');
INSERT INTO AI_USERS VALUES ('bob', 0, 1, 1, 101, 40, 'EAST');
COMMIT;
```

#### 4. LDAP Setup

Configure LDAP server with matching users (usernames must exist in both LDAP and AI_USERS).

#### 5. Run Application

```bash
python -m backend.main
```

Access at: [http://localhost:8000](http://localhost:8000)

---

## 11. Workflow Diagrams

### Complete Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Browser
    participant auth.js
    participant Flask
    participant HybridResolver
    participant LDAP
    participant Oracle
    
    User->>Browser: Opens http://localhost:8000
    Browser->>Flask: GET /
    Flask->>Flask: Load templates.py
    Flask->>Flask: Inject UI text & config
    Flask-->>Browser: Return rendered base.html
    Browser->>Browser: Load auth.js
    auth.js->>auth.js: Check vanna_user cookie
    auth.js-->>Browser: Show login form
    
    User->>Browser: Enters username/password
    Browser->>auth.js: Submit form
    auth.js->>auth.js: Base64 encode credentials
    auth.js->>Flask: POST /auth_test (Authorization header)
    
    Flask->>HybridResolver: resolve_user(request_context)
    HybridResolver->>HybridResolver: Decode Basic Auth
    HybridResolver->>LDAP: Bind as uid=alice,ou=users,...
    LDAP-->>HybridResolver: Success + email
    
    HybridResolver->>Oracle: SELECT IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER FROM AI_USERS WHERE USERNAME='alice'
    Oracle-->>HybridResolver: (0, 0, 1)
    HybridResolver->>HybridResolver: Map to groups: ['user']
    HybridResolver-->>Flask: User(id='alice', groups=['user'])
    
    Flask-->>auth.js: 200 OK { user: 'alice', groups: ['user'] }
    auth.js->>auth.js: Set cookies (vanna_user, vanna_auth, vanna_groups)
    auth.js->>Browser: Hide login, show chat
```

### SQL Execution with RLS

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Chat as <vanna-chat>
    participant Flask
    participant Agent
    participant Prompt as SystemPromptBuilder
    participant RLS as RLSService
    participant Tool as SecureRunSqlTool
    participant Oracle
    
    User->>Chat: "Show all employees"
    Chat->>Flask: SSE Request (Authorization header)
    Flask->>Agent: handle_message(user_context)
    
    Agent->>Prompt: build_system_prompt(user, tools)
    Prompt->>RLS: get_user_filter_values('alice')
    RLS->>Oracle: SELECT EMPLOYEE_ID, DEPARTMENT_ID FROM AI_USERS WHERE USERNAME='alice'
    Oracle-->>RLS: (100, 30)
    RLS-->>Prompt: {EMPLOYEE_ID: 100, DEPARTMENT_ID: 30}
    Prompt-->>Agent: System prompt with RLS context
    
    Agent->>LLM: Send prompt + user query
    LLM-->>Agent: Tool call: run_sql("SELECT * FROM employees")
    Agent->>Tool: execute(context, args)
    
    Tool->>Tool: Check user.group_memberships
    alt User is admin/superuser
        Tool->>Oracle: Execute original SQL
    else User is normal user
        Tool->>RLS: apply_rls_filters(sql, user_filter_values)
        RLS->>RLS: Parse SQL, extract tables
        RLS->>Oracle: Get table columns for 'employees'
        Oracle-->>RLS: [EMPLOYEE_ID, DEPARTMENT_ID, NAME, ...]
        RLS->>RLS: Match filter columns
        RLS->>RLS: Inject WHERE clause
        RLS-->>Tool: Modified SQL + bind params
        Tool->>Oracle: Execute filtered SQL
    end
    
    Oracle-->>Tool: ResultSet (filtered)
    Tool-->>Agent: DataFrame component
    Agent-->>Flask: Stream results
    Flask-->>Chat: SSE: DataFrame JSON
    Chat->>Chat: Render table
```

### Schema Training Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Chat
    participant Agent
    participant Tool as GatherSchemaTool
    participant Trainer as SchemaTrainer
    participant Oracle
    participant LLM
    participant Milvus
    
    User->>Chat: "/gather"
    Chat->>Agent: Parse command
    Agent->>Tool: execute(context, args)
    Tool->>Tool: Check user permissions
    Tool->>Trainer: train_schema()
    
    Trainer->>Oracle: SELECT tables, columns FROM USER_TAB_COLUMNS
    Oracle-->>Trainer: Metadata for 15 tables
    
    loop For each table
        Trainer->>Trainer: generate_ddl(table_info)
        Trainer->>Oracle: SELECT * FROM table WHERE ROWNUM <= 20
        Oracle-->>Trainer: Sample rows
        Trainer->>LLM: Analyze table and describe purpose
        LLM-->>Trainer: "This table stores employee information..."
        Trainer->>Milvus: save_text_memory(ddl + description)
    end
    
    Trainer->>Trainer: generate_relationship_summary()
    Trainer->>Milvus: save_text_memory(relationships)
    
    Trainer-->>Tool: items_trained = 15
    Tool-->>Agent: ToolResult(success=True, "Trained 15 objects")
    Agent-->>Chat: "Schema training completed successfully..."
```

---

## Appendix A: Backend UI Overrides

> **⚠️ CRITICAL**: This section documents all places where the backend code overrides or customizes the default Vanna UI behavior. These overrides are essential for understanding how the UI actually works versus standard Vanna installations.

### Overview

The backend implements **4 major UI overrides** that fundamentally change the user experience:

1. **Custom Index Route Override** - Replaces default Vanna UI with LDAP login
2. **Workflow Handler Disabling** - Removes "Admin View" message
3. **System Prompt Builder Customization** - Injects user context into LLM
4. **Custom Authentication Endpoint** - Adds `/auth_test` route

---

### 1. Custom Index Route Override

**Location**: `backend/main.py` lines 106-118

**What It Does**: Completely replaces the default Vanna index page with custom LDAP login interface.

**Code**:
```python
# Define custom LDAP login view function
def custom_index() -> str:
    api_base_url = self.config.get("api_base_url", "")
    show_api_endpoints = config.ui.show_api_endpoints
    ui_text = config.ui.text
    return get_ldap_login_html(
        api_base_url=api_base_url,
        show_api_endpoints=show_api_endpoints,
        ui_text=ui_text
    )

# Override the default index view function with our custom one
app.view_functions['index'] = custom_index
```

**Impact**:
- **Default Vanna**: Shows chat interface immediately (demo mode)
- **This Application**: Shows login form first, requires LDAP authentication
- **UI Flow**: User cannot access chat until authenticated

**Why This Exists**:
- Vanna's default `register_chat_routes()` (line 104) creates an `index` route
- We call it first to register all other routes
- Then we **override** the `index` view function to use our custom login

**Template Processing**: The `custom_index()` function calls `get_ldap_login_html()` which:
1. Loads `base.html` from assets
2. Injects all UI text from `config.ui.text` (48+ variables)
3. Loads and injects `auth.js` and `styles.css`
4. Returns complete HTML with all placeholders replaced

**Bypassing This Override**: To restore default Vanna UI, simply comment out line 118:
```python
# app.view_functions['index'] = custom_index  # Restore default Vanna UI
```

---

### 2. Workflow Handler Disabling

**Location**: `backend/main.py` lines 544-552

**What It Does**: Disables Vanna's default workflow handler that displays role-based welcome messages.

**Code**:
```python
# Create and return the agent
# Note: workflow_handler=None disables the default handler that shows "Admin View"
# message based on group membership
agent = Agent(
    llm_service=llm,
    tool_registry=tools,
    user_resolver=user_resolver,
    agent_memory=agent_memory,
    config=agent_config,
    workflow_handler=None,  # Disable default workflow handler
    system_prompt_builder=system_prompt_builder  # User-aware prompts
)
```

**Impact**:
- **Default Vanna**: Shows "Admin View - You are logged in as an administrator" message when admin users log in
- **This Application**: No role-based welcome messages displayed
- **UI Behavior**: Cleaner interface without automatic role announcements

**Why This Exists**:
- The default workflow handler was showing confusing messages
- User issue referenced in conversation history: "Fixing Admin View Message"
- Decision was made to rely on backend role enforcement without UI notification

**Re-Enabling**: To restore default behavior:
```python
workflow_handler=DefaultWorkflowHandler(),  # Re-enable
```

**Related Files**: 
- Conversation `eb6c79bb-3a28-41d0-8746-8ab192933886` documents the fix
- User complained that 'testuser' saw "Admin View" despite not being admin

---

### 3. System Prompt Builder Customization

**Location**: `backend/main.py` lines 533-540, `backend/system_prompt_builder.py` (entire file - 318 lines)

**What It Does**: Injects extensive user context into every LLM interaction, fundamentally changing how the AI understands queries.

**Code (main.py)**:
```python
# Create user-aware system prompt builder
# This injects user identity and RLS filter values into the LLM prompt
# Schema information is retrieved via semantic search from agent memory when needed
system_prompt_builder = UserAwareSystemPromptBuilder(
    rls_service=rls_service,
    company_name="Database Chat",
    include_rls_values=True
)
```

**Code (system_prompt_builder.py excerpt)**:
```python
async def build_system_prompt(self, user: User, tools: List[Any]) -> Optional[str]:
    """Build the system prompt with user context included."""
    # Start with base prompt (await since it's async)
    base_prompt = await self._default_builder.build_system_prompt(user, tools)
    
    # Build user context section
    user_context = self._build_user_context(user)
    
    # Combine prompts
    full_prompt = f"""{base_prompt}

## Current User Context

{user_context}

## Important Instructions for User Queries

When the user asks about "my data", "my details", "my records"...
1. **You already know who they are** - Use the user information provided above
2. **Do NOT ask for their user ID or email** - You have this information
...
"""
    return full_prompt
```

**Impact on UI Experience**:

| Query | Default Vanna Behavior | With UserAwareSystemPromptBuilder |
|-------|------------------------|-----------------------------------|
| "Show my salary" | Asks: "What is your employee ID?" | Immediately queries: `SELECT salary FROM employees WHERE employee_id = 100` |
| "Give me my details" | Asks: "Which details? Can you be more specific?" | Uses known identity: `SELECT * FROM employees WHERE email = 'alice@company.com'` |
| "Is my salary good?" | Generic response | Compares salary to job range using `JOIN JOBS` |

**User Context Injected** (example for user 'alice'):
```markdown
## Current User Context

**Username:** alice
**Email:** alice@company.com
**Groups/Roles:** user
**Access Level:** NORMALUSER - Row-Level Security (RLS) Applied

⚠️ IMPORTANT: RLS Authorization Restrictions

This user belongs to the NORMALUSER group and has the following restrictions:
- **Can ONLY access data belonging to them**
- **Unauthorized to access other users' data**
- **RLS is enforced at the database level**

**User Identity Columns:**
- EMPLOYEE_ID: 100
- DEPARTMENT_ID: 30
- REGION_ID: WEST
```

**Special Prompt Sections Added**:

1. **RLS Instructions for NORMALUSER** (124 lines):
   - Explains row-level security restrictions
   - Instructs LLM how to handle unauthorized data requests
   - Provides polite rejection messages: *"I can only access data that belongs to you due to row-level security restrictions"*

2. **Visualization Guidelines** (64 lines):
   - Instructs LLM to **automatically** create charts for aggregate queries
   - Specifies when to use bar/line/pie charts
   - Example: "Show sales by month" → Auto-creates line chart

3. **Query Guidelines** (20 lines):
   - Explains automatic RLS filtering
   - Provides JOIN examples
   - Clarifies when to inform users about restrictions

**Why This Exists**:
- **Personalization**: Enables conversational queries without redundant questions
- **Security Awareness**: LLM understands and explains RLS to users
- **UX Enhancement**: Auto-visualization improves data comprehension

**Files Involved**:
- `backend/system_prompt_builder.py`: The custom builder class (318 lines)
- `backend/main.py`: Instantiation and registration (lines 533-540)
- `backend/rls_service.py`: Provides user filter values (lines 145-202)

---

### 4. Custom Authentication Endpoint

**Location**: `backend/main.py` lines 120-166

**What It Does**: Adds a new `/api/vanna/v2/auth_test` endpoint that doesn't exist in default Vanna.

**Code**:
```python
# Auth test endpoint for LDAP validation
@app.route("/api/vanna/v2/auth_test", methods=["POST"])
def auth_test():
    """Test LDAP authentication and return user info."""
    import asyncio
    
    # Create request context
    request_context = RequestContext(
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        remote_addr=request.remote_addr,
        query_params=dict(request.args),
    )
    
    # Resolve user using the agent's user resolver
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        user = loop.run_until_complete(
            self.agent.user_resolver.resolve_user(request_context)
        )
        
        # Check if user is guest (auth failed)
        if user.id == config.ldap.guest_username:
            return jsonify({"error": "Invalid username or password..."}), 401
        
        return jsonify({
            "success": True,
            "user": user.id,
            "email": user.email,
            "groups": user.group_memberships,
            "is_admin": 'admin' in user.group_memberships
        })
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 401
    finally:
        loop.close()
```

**Impact**:
- **Default Vanna**: No authentication testing endpoint
- **This Application**: Frontend can validate credentials before showing chat
- **UI Flow**: Login button calls this endpoint → validates → shows chat or error

**Frontend Integration**:
- Called by `auth.js` line 62: `fetch('/api/vanna/v2/auth_test', ...)`
- Request includes `Authorization: Basic <credentials>`
- Response determines UI state (show chat vs. show error)

**Why This Exists**:
- Separates authentication from chat functionality
- Allows frontend to test credentials without initializing chat
- Provides clean error messages for invalid logins

**Security Features**:
1. **LDAP Validation**: Calls `HybridUserResolver` which checks LDAP
2. **Database Verification**: Ensures user exists in `AI_USERS` table
3. **Guest Rejection**: Rejects if user resolves to guest account
4. **Error Handling**: Catches LDAP errors and DB errors separately

---

### 5. Custom Assets Route

**Location**: `backend/main.py` lines 70-96

**What It Does**: Adds custom static file serving for `assets/` folder.

**Code**:
```python
# Serve assets folder as static files
assets_path = Path(__file__).parent.parent / "assets"
if assets_path.exists():
    @app.route("/assets/<path:filepath>")
    def assets(filepath):
        """Serve files from the assets directory."""
        # Normalize path separators
        filepath = filepath.replace('\\', '/')
        # Build the full path
        full_path = assets_path / filepath
        # Resolve to absolute path to prevent directory traversal
        try:
            full_path = full_path.resolve()
            assets_path_resolved = assets_path.resolve()
            # Ensure the file is within the assets directory
            if not str(full_path).startswith(str(assets_path_resolved)):
                abort(404)
            if full_path.exists() and full_path.is_file():
                directory = str(full_path.parent)
                filename = full_path.name
                return send_from_directory(directory, filename)
        except (ValueError, OSError):
            pass
        abort(404)
```

**Impact**:
- **Default Vanna**: Static files served from package resources
- **This Application**: Custom assets served from project `assets/` folder
- **Enables**: Custom fonts, CSS, JS, HTML templates

**Security Features**:
- Path traversal protection (lines 88-89)
- Windows/Linux path normalization (line 80)
- Absolute path resolution (line 85)
- Directory containment check (line 88)

**Files Served**:
- `/assets/base.html` → Main template
- `/assets/css/styles.css` → Custom CSS
- `/assets/css/google-fonts.css` → Font definitions
- `/assets/js/auth.js` → Authentication logic
- `/assets/js/tailwindcss.js` → TailwindCSS framework
- `/assets/js/vanna-components.js` → Chat component
- `/assets/fonts/*.ttf` → Self-hosted fonts (11 files)

---

### 6. Health Check Route Override

**Location**: `backend/main.py` lines 168-171

**What It Does**: Overrides default health check endpoint with custom response.

**Code**:
```python
# Health check (override)
@app.route("/health")
def health_check():
    return {"status": "healthy", "service": "vanna"}
```

**Impact**:
- **Default Vanna**: May not have health check, or different format
- **This Application**: Simple JSON response for monitoring
- **Use Case**: Docker health checks, load balancer probes

---

### Summary of UI Overrides

| Override | File | Lines | Impact | Revert Method |
|----------|------|-------|--------|---------------|
| **Index Route** | `main.py` | 106-118 | Login required before chat | Comment line 118 |
| **Workflow Handler** | `main.py` | 544-552 | No "Admin View" message | Change `None` to `DefaultWorkflowHandler()` |
| **System Prompt** | `system_prompt_builder.py` | 1-318 | User-aware queries, auto-viz | Use `DefaultSystemPromptBuilder()` |
| **Auth Endpoint** | `main.py` | 120-166 | LDAP validation endpoint | Remove route decorator |
| **Assets Route** | `main.py` | 70-96 | Custom static files | Remove route, use default |
| **Health Check** | `main.py` | 168-171 | Custom health response | Remove route decorator |

---

### Configuration-Based UI Customization

In addition to code overrides, the UI is heavily customized via **environment variables** in `backend/config.py`:

**48 UI Text Variables** (lines 213-286):
```python
@dataclass
class UITextConfig:
    page_title: str = "Agents Chat"
    header_title: str = "Agents"
    login_button: str = "Login"
    # ... 45 more customizable strings
```

**All customizable via `.env`**:
```bash
UI_PAGE_TITLE=My Custom App
UI_HEADER_TITLE=Data Intelligence
UI_LOGIN_BUTTON=Sign In
# ... etc
```

**Impact**: Entire UI can be rebranded without touching code.

---

### Testing Override Behavior

**To test default Vanna UI**:
1. Comment out line 118 in `main.py`: `# app.view_functions['index'] = custom_index`
2. Restart server
3. Visit `http://localhost:8000` → Should see default Vanna chat (no login)

**To test without RLS prompts**:
1. Change line 553 in `main.py`: `system_prompt_builder=None`
2. Restart server
3. LLM will not have user context or RLS instructions

**To re-enable "Admin View" message**:
1. Import: `from vanna.workflows import DefaultWorkflowHandler`
2. Change line 552: `workflow_handler=DefaultWorkflowHandler()`
3. Restart server
4. Admin users will see welcome message

---

## Appendix: Complete File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `backend/main.py` | 588 | Flask server, HybridUserResolver, Agent setup |
| `backend/config.py` | 420 | Configuration management (Oracle, LDAP, UI, RLS) |
| `backend/rls_service.py` | 516 | Row-level security implementation |
| `backend/system_prompt_builder.py` | 318 | User-aware system prompt generation |
| `backend/schema_trainer.py` | 637 | Database schema training to Milvus |
| `backend/secure_sql_tool.py` | 253 | SQL execution with RLS filtering |
| `backend/discover_tables_tool.py` | 305 | List all database tables (/discover) |
| `backend/templates.py` | 112 | HTML template generation |
| `backend/gather_schema_tool.py` | 70 | Schema training tool (/gather) |
| `backend/cleanup_memory_tool.py` | 80 | Memory cleanup tool (/cleanup) |
| `assets/base.html` | 127 | Main HTML template |
| `assets/js/auth.js` | 139 | Authentication logic |
| `assets/js/vanna-components.js` | ~7.6MB | Chat Web Component |
| `assets/css/styles.css` | 525B | Custom CSS overrides |

---

**End of Documentation**

*Last Updated: 2025-12-30*  
*Version: 1.0 (Comprehensive)*
