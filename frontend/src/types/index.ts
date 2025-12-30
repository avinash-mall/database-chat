// =============================================================================
// API Request/Response Types
// =============================================================================

export interface ChatRequest {
    message: string;
    conversation_id?: string;
    request_id?: string;
    request_context?: Record<string, any>;
    metadata?: Record<string, any>;
}

export interface RequestContext {
    cookies: Record<string, string>;
    headers: Record<string, string>;
    remote_addr: string | null;
    query_params: Record<string, string>;
    metadata: Record<string, any>;
}

// Vanna 2.0 UI Component Types
export interface VannaComponent {
    id: string;
    type: string;  // status_card, task_tracker_update, text, code, dataframe, etc.
    lifecycle?: 'create' | 'update' | 'complete' | 'error';
    title?: string;
    subtitle?: string;
    description?: string;
    content?: string;
    text?: string;
    children?: VannaComponent[];
    timestamp?: string;
    metadata?: Record<string, any>;
    // Component-specific fields
    code?: string;
    language?: string;
    data?: any[];
    columns?: string[];
    layout?: any;
    status?: string;
    progress?: number;
    [key: string]: any;  // Allow additional fields
}

export interface ChatStreamChunk {
    // Old format (legacy support)
    rich?: any;
    simple?: string | any;
    // New Vanna 2.0 component format
    id?: string;
    type?: string;
    lifecycle?: 'create' | 'update' | 'complete' | 'error';
    title?: string;
    subtitle?: string;
    description?: string;
    content?: string;
    text?: string;
    children?: VannaComponent[];
    // Component-specific fields
    code?: string;
    language?: string;
    data?: any[];
    columns?: string[];
    layout?: any;
    status?: string;
    progress?: number;
    // Common fields
    conversation_id?: string;
    request_id?: string;
    timestamp?: string | number;
    metadata?: Record<string, any>;
    [key: string]: any;  // Allow additional fields for flexibility
}

export interface ChatResponse {
    chunks: ChatStreamChunk[];
    conversation_id: string;
    request_id: string;
    total_chunks: number;
}

export interface AuthResponse {
    success: boolean;
    user: string;
    email: string;
    groups: string[];
    is_admin: boolean;
}

// ===== Message Types =====

export type MessageRole = 'user' | 'assistant' | 'system' | 'error';

export interface BaseMessage {
    id: string;
    role: MessageRole;
    timestamp: number;
    metadata?: Record<string, any>;
}

export interface UserMessage extends BaseMessage {
    role: 'user';
    content: string;
}

export interface AssistantMessage extends BaseMessage {
    role: 'assistant';
    content: MessageContent[];
    toolCalls?: ToolExecution[];
    thinking?: ThinkingStep[];
}

export interface ErrorMessage extends BaseMessage {
    role: 'error';
    error: string;
    details?: string;
}

export type Message = UserMessage | AssistantMessage | ErrorMessage;

// ===== Content Types =====

export type MessageContent =
    | TextContent
    | CodeContent
    | DataFrameContent
    | PlotlyContent
    | UnknownContent;

export interface TextContent {
    type: 'text';
    content: string;
}

export interface CodeContent {
    type: 'code';
    code: string;
    language: string;
}

export interface DataFrameContent {
    type: 'dataframe';
    data: any[];
    columns: string[];
}

export interface PlotlyContent {
    type: 'plotly';
    data: any;
    layout: any;
}

export interface UnknownContent {
    type: 'unknown';
    rawData: any;
    label: string;
}

// ===== Tool Execution Types =====

export interface ToolExecution {
    id: string;
    name: string;
    arguments: Record<string, any>;
    result?: any;
    status: 'executing' | 'complete' | 'error';
    duration?: number;
    error?: string;
}

export interface ThinkingStep {
    step: number;
    description: string;
    status: 'pending' | 'in-progress' | 'complete';
}

// ===== Conversation Types =====

export interface Conversation {
    id: string;
    title: string;
    messages: Message[];
    createdAt: number;
    updatedAt: number;
}

// ===== User & Auth Types =====

export interface User {
    id: string;
    username: string;
    email: string;
    groups: string[];
    isAdmin: boolean;
}

export interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    token: string | null;
}

// ===== UI Config Types =====

export interface UIConfig {
    pageTitle: string;
    headerTitle: string;
    headerSubtitle: string;
    headerDescription: string;
    loginTitle: string;
    loginDescription: string;
    chatTitle: string;
    showApiEndpoints: boolean;
    apiBaseUrl: string;
    // Additional UI text fields
    usernameLabel?: string;
    passwordLabel?: string;
    loginButton?: string;
    logoutButton?: string;
    loggedInPrefix?: string;
}

// ===== Connection Types =====

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';
export type StreamingStatus = 'idle' | 'streaming' | 'complete' | 'error';

// ===== Store State Types =====

export interface ChatState {
    conversations: Record<string, Conversation>;
    activeConversationId: string | null;
    isStreaming: boolean;
    currentStreamingMessage: Partial<AssistantMessage> | null;
    connectionStatus: ConnectionStatus;
    streamingStatus: StreamingStatus;
}

export interface UIState {
    config: UIConfig | null;
    theme: 'light' | 'dark';
    sidebarCollapsed: boolean;
}

// ===== Utility Types =====

export interface ApiError {
    error: string;
    details?: string;
    status?: number;
}
