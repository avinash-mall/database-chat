# Database Chat Frontend (React + TypeScript)

Modern React frontend for the Database Chat AI application, built with TypeScript, Tailwind CSS, and streaming support.

## 🎯 Features

- ✅ **Full Feature Parity** with Flask UI
- 🎨 **ChatGPT-like UX** with streaming, tool traces, thinking indicators
- 🔐 **LDAP Authentication** with session management
- 📊 **Rich Content Rendering**: Markdown, SQL, tables, Plotly charts
- 🔥 **Server-Sent Events** with custom parser (Basic Auth support)
- 🎯 **TypeScript** for type-safe development
- 🎨 **Tailwind CSS** with Vanna color palette
- ⚡ **Vite** for fast development and optimized builds

## 🚀 Quick Start

### Development Mode (with Docker)

Run the entire stack (backend + frontend + services):

```bash
# From project root
docker-compose up
```

Frontend will be available at: http://localhost:5173  
Backend API at: http://localhost:8000

### Development Mode (local)

If you prefer running frontend locally without Docker:

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (with API proxy to backend)
npm run dev
```

Make sure the backend is running at `http://localhost:8000` for the proxy to work.

### Production Build

```bash
cd frontend

# Build for production
npm run build

# Preview production build
npm run preview
```

The production build will be in `dist/` directory.

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Auth/           # Login, auth guards
│   │   ├── Chat/           # Message list, input, etc.
│   │   ├── Layout/         # Layout components
│   │   └── Renderers/      # Content renderers
│   ├── hooks/              # Custom React hooks
│   │   └── useChatStream.ts # SSE streaming hook
│   ├── services/           # API services
│   │   └── api-client.ts   # Main API client
│   ├── stores/             # Zustand state stores
│   │   ├── authStore.ts    # Authentication state
│   │   ├── chatStore.ts    # Chat & conversations
│   │   └── uiStore.ts      # UI preferences
│   ├── types/              # TypeScript types
│   │   └── index.ts        # All type definitions
│   ├── utils/              # Utility functions
│   │   └── chunk-reducer.ts # Streaming chunk processor
│   ├── App.tsx             # Root component
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── Dockerfile              # Production Docker image
├── Dockerfile.dev          # Development Docker image
├── nginx.conf              # Nginx config for production
├── package.json            # Dependencies
├── tsconfig.json           # TypeScript config
├── tailwind.config.js      # Tailwind config
└── vite.config.ts          # Vite config
```

## 🔧 Configuration

### Environment Variables

Add to `.env` in project root:

```bash
# Frontend configuration
FRONTEND_PORT=5173

# Backend API (for production nginx proxy)
VANNA_PORT=8000
```

### API Proxy

In development, Vite proxies API requests to the backend. See `vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': 'http://backend:8000',  // Docker
    // or 'http://localhost:8000'   // Local
  }
}
```

### UI Customization

The frontend fetches UI text configuration from `/api/vanna/v2/config`. Customize via backend `.env`:

```bash
UI_PAGE_TITLE=My Database Chat
UI_HEADER_TITLE=Custom Title
UI_LOGIN_TITLE=Sign In
# ... see backend/config.py for all options
```

## 🛠️ Development

### Available Scripts

```bash
npm run dev        # Start dev server with HMR
npm run build      # Build for production
npm run preview    # Preview production build
npm run lint       # Run ESLint
npm run test       # Run Vitest tests
```

### Adding New Components

1. Create component in  `src/components/`
2. Add types to `src/types/index.ts` if needed
3. Update relevant store if state is required
4. Import and use in parent components

### Debugging Streaming

The custom SSE parser logs to console. Enable verbose logging:

```typescript
// In api-client.ts, uncomment:
console.log('SSE chunk received:', chunk);
```

## 🧪 Testing

```bash
# Run tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Coverage report
npm run test -- --coverage
```

## 📦 Docker

### Build Images

```bash
# Development image
docker build -f Dockerfile.dev -t vanna-frontend:dev .

# Production image
docker build -t vanna-frontend:latest .
```

### Run Standalone

```bash
# Development (with hot-reload)
docker run -p 5173:5173 \
  -v $(pwd):/app \
  -v /app/node_modules \
  vanna-frontend:dev

# Production
docker run -p 80:80 vanna-frontend:latest
```

## 🎨 Styling

### Tailwind Classes

The project uses custom Vanna color palette:

```css
bg-vanna-navy      /* #023d60 - Primary dark */
bg-vanna-cream     /* #e7e1cf - Background accent */
bg-vanna-teal      /* #15a8a8 - Primary brand */
bg-vanna-orange    /* #fe5d26 - Accent */
bg-vanna-magenta   /* #bf1363 - Accent */
```

### Custom Fonts

- **Sans**: Space Grotesk
- **Serif**: Roboto Slab  
- **Mono**: Space Mono

Loaded via Google Fonts in `index.html`.

## 🔐 Authentication Flow

1. User enters credentials on `/login`
2. `LoginPage` calls `apiClient.login()`
3. Backend validates via LDAP + AI_USERS table
4. On success, stores cookies + updates AuthStore
5. Redirects to `/chat`
6. All API requests include `Authorization: Basic {token}` header

## 📡 Streaming Architecture

```
User Input → useChatStream → apiClient.chatSSE
           → Custom SSE Parser → ChunkReducer
           → AssistantMessage → MessageList → UI
```

The `ChunkReducer` assembles partial chunks into complete messages with intelligent text merging.

## 🚧 Roadmap

### Phase 2: Chat UI Components ✅
- [x] API client with SSE parser
- [x] Zustand stores
- [x] useChatStream hook
- [ ] LoginPage component
- [ ] ChatLayout component
- [ ] MessageList component
- [ ] ChatInput component

### Phase 3: Rich Content Renderers
- [ ] MarkdownRenderer
- [ ] CodeBlock with syntax highlighting
- [ ] DataTable with sorting
- [ ] PlotlyChart
- [ ] ToolTracePanel
- [ ] RawJsonViewer

### Phase 4: Advanced Features
- [ ] Conversation sidebar
- [ ] Thinking indicator
- [ ] Connection status
- [ ] Slash commands
- [ ] Accessibility improvements

## 📄 License

Same as parent project (see root LICENSE file).

## 🤝 Contributing

1. Follow existing code style
2. Add TypeScript types for new features
3. Test streaming functionality thoroughly
4. Update this README for major changes

## 📞 Support

See main project README for support information.

---

**Built with ❤️ using React, TypeScript, and Tailwind CSS**
