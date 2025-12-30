import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    AuthResponse,
    RequestContext,
    UIConfig,
    ApiError,
} from '@/types';

/**
 * API Client for Database Chat application
 * 
 * Features:
 * - Basic Auth with automatic header injection
 * - Custom SSE streaming parser (supports Authorization headers)
 * - Polling fallback
 * - Cookie-based session management
 * - Request ID generation
 */
class ApiClient {
    private client: AxiosInstance;
    private baseURL: string;

    constructor(baseURL: string = '') {
        this.baseURL = baseURL;
        this.client = axios.create({
            baseURL,
            headers: { 'Content-Type': 'application/json' },
            withCredentials: true, // Send cookies
        });

        // Request interceptor: Add Basic Auth token from storage
        this.client.interceptors.request.use((config) => {
            const authToken = this.getAuthToken();
            if (authToken && !config.headers['Authorization']) {
                config.headers['Authorization'] = `Basic ${authToken}`;
            }
            return config;
        });

        // Response interceptor: Handle 401 unauthorized
        this.client.interceptors.response.use(
            (response) => response,
            (error: AxiosError<ApiError>) => {
                if (error.response?.status === 401) {
                    // Clear auth and redirect to login
                    this.clearAuth();
                    if (window.location.pathname !== '/login') {
                        window.location.href = '/login';
                    }
                }
                return Promise.reject(error);
            }
        );
    }

    // ===== Authentication =====

    async login(username: string, password: string): Promise<AuthResponse> {
        const credentials = btoa(`${username}:${password}`);

        try {
            const response = await this.client.post<AuthResponse>(
                '/api/vanna/v2/auth_test',
                { test: true },
                { headers: { 'Authorization': `Basic ${credentials}` } }
            );

            // Store auth token
            this.setAuthToken(credentials);
            this.setCookie('vanna_user', username);
            this.setCookie('vanna_groups', response.data.groups.join(','));

            return response.data;
        } catch (error) {
            const axiosError = error as AxiosError<ApiError>;
            throw new Error(
                axiosError.response?.data?.error || 'Authentication failed'
            );
        }
    }

    logout(): void {
        this.clearAuth();
        window.location.href = '/login';
    }

    // ===== Streaming Chat (SSE) =====

    /**
     * Send message via Server-Sent Events streaming
     * Uses custom fetch-based SSE parser to support Authorization headers
     * 
     * @returns AbortController for canceling the stream
     */
    async chatSSE(
        message: string,
        conversationId: string | null,
        onChunk: (chunk: ChatStreamChunk) => void,
        onComplete: () => void,
        onError: (error: Error) => void
    ): Promise<AbortController> {
        const requestId = this.generateRequestId();
        const controller = new AbortController();

        const requestBody: ChatRequest = {
            message,
            conversation_id: conversationId,
            request_id: requestId,
            request_context: this.buildRequestContext(),
            metadata: {},
        };

        try {
            const authToken = this.getAuthToken();
            const response = await fetch(`${this.baseURL}/api/vanna/v2/chat_sse`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Basic ${authToken}`,
                },
                body: JSON.stringify(requestBody),
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            if (!response.body) {
                throw new Error('Response body is null');
            }

            // Parse SSE stream
            await this.parseSSEStream(response.body, onChunk, onComplete, onError);
        } catch (error) {
            if ((error as Error).name !== 'AbortError') {
                onError(error as Error);
            }
        }

        return controller;
    }

    /**
     * Custom SSE parser using fetch() API
     * Works around EventSource limitations with custom headers
     */
    private async parseSSEStream(
        stream: ReadableStream<Uint8Array>,
        onChunk: (chunk: ChatStreamChunk) => void,
        onComplete: () => void,
        onError: (error: Error) => void
    ): Promise<void> {
        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim(); // Remove 'data: ' prefix

                        if (data === '[DONE]') {
                            onComplete();
                            return;
                        }

                        if (data) {
                            try {
                                const chunk = JSON.parse(data) as ChatStreamChunk;
                                onChunk(chunk);
                            } catch (e) {
                                console.warn('Failed to parse SSE chunk:', data, e);
                            }
                        }
                    }
                }
            }

            onComplete();
        } catch (error) {
            if ((error as Error).name !== 'AbortError') {
                onError(error as Error);
            }
        } finally {
            reader.releaseLock();
        }
    }

    // ===== Polling Fallback =====

    async chatPoll(
        message: string,
        conversationId: string | null
    ): Promise<ChatResponse> {
        const requestId = this.generateRequestId();
        const requestBody: ChatRequest = {
            message,
            conversation_id: conversationId,
            request_id: requestId,
            request_context: this.buildRequestContext(),
            metadata: {},
        };

        try {
            const response = await this.client.post<ChatResponse>(
                '/api/vanna/v2/chat_poll',
                requestBody
            );
            return response.data;
        } catch (error) {
            const axiosError = error as AxiosError<ApiError>;
            throw new Error(
                axiosError.response?.data?.error || 'Chat request failed'
            );
        }
    }

    // ===== Configuration =====

    async getConfig(): Promise<UIConfig> {
        try {
            const response = await this.client.get<UIConfig>('/api/vanna/v2/config');
            return response.data;
        } catch (error) {
            console.warn('Failed to fetch UI config, using defaults', error);
            // Return default config
            return {
                pageTitle: 'Database Chat AI',
                headerTitle: 'Agents',
                headerSubtitle: 'DATA-FIRST AGENTS',
                headerDescription: 'Interactive AI Assistant for Database Queries',
                loginTitle: 'Login to Continue',
                loginDescription: 'Enter your credentials to access the chat',
                chatTitle: 'Oracle Database AI Chat',
                showApiEndpoints: false,
                apiBaseUrl: '',
            };
        }
    }

    // ===== Utility Methods =====

    private getAuthToken(): string | null {
        return this.getCookie('vanna_auth') || localStorage.getItem('vanna_auth');
    }

    private setAuthToken(token: string): void {
        this.setCookie('vanna_auth', token, 365);
        localStorage.setItem('vanna_auth', token);
    }

    private clearAuth(): void {
        this.deleteCookie('vanna_auth');
        this.deleteCookie('vanna_user');
        this.deleteCookie('vanna_groups');
        localStorage.removeItem('vanna_auth');
    }

    private getCookie(name: string): string | null {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop()!.split(';').shift() || null;
        }
        return null;
    }

    private setCookie(name: string, value: string, days: number = 365): void {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
    }

    private deleteCookie(name: string): void {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }

    private generateRequestId(): string {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    private buildRequestContext(): RequestContext {
        return {
            cookies: this.getAllCookies(),
            headers: {
                'User-Agent': navigator.userAgent,
            },
            remote_addr: null,
            query_params: {},
            metadata: {},
        };
    }

    private getAllCookies(): Record<string, string> {
        return document.cookie.split(';').reduce((acc, cookie) => {
            const [key, value] = cookie.trim().split('=');
            if (key) acc[key] = value || '';
            return acc;
        }, {} as Record<string, string>);
    }
}

// Export singleton instance
export const apiClient = new ApiClient();
