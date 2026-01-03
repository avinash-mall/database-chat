import type {
    ChatStreamChunk,
    AssistantMessage,
    MessageContent,
    ToolExecution,
    VannaComponent,
} from '@/types';

/**
 * Chunk Reducer - Stateful processor for streaming message chunks
 * 
 * Supports both legacy format (rich/simple) and Vanna 2.0 component format
 * Intelligently merges text streams and handles rich content types
 */
export class ChunkReducer {
    private messageBuffer: Partial<AssistantMessage> = {
        id: '',
        role: 'assistant',
        content: [],
        metadata: {},
        toolCalls: [],
        timestamp: Date.now(),
    };

    // Track UI components we should ignore (not render as content)
    private uiComponentTypes = new Set([
        'status_bar_update',
        'task_tracker_update',
        'chat_input_update',
        'status_card',
        'ui_update',
        'system_update',
        'workflow_update',
        'card',           // Card components (progress, info cards)
        'notification',   // Notification/toast messages
    ]);

    /**
   * Process a single chunk and update message buffer
   */
    processChunk(chunk: ChatStreamChunk): Partial<AssistantMessage> {
        // DEBUG: Log every chunk
        console.log('[CHUNK-REDUCER] Received chunk:', chunk);
        console.log('[CHUNK-REDUCER] Has type?', !!chunk.type, 'Type:', chunk.type);
        console.log('[CHUNK-REDUCER] Has id?', !!chunk.id, 'ID:', chunk.id);
        console.log('[CHUNK-REDUCER] Has rich?', !!chunk.rich);
        console.log('[CHUNK-REDUCER] Has simple?', !!chunk.simple);

        // Initialize ID and metadata from first chunk
        if (!this.messageBuffer.id && chunk.request_id) {
            this.messageBuffer.id = chunk.request_id;
            this.messageBuffer.metadata!.conversation_id = chunk.conversation_id;
            this.messageBuffer.metadata!.request_id = chunk.request_id;
        }

        // Detect format:
        // Vanna 2.0 can be:
        // 1. Direct component: chunk.type exists
        // 2. Wrapped in rich: chunk.rich.type exists
        const isDirectVanna2 = !!chunk.type;
        const isWrappedVanna2 = chunk.rich && typeof chunk.rich === 'object' && 'type' in chunk.rich;
        const hasLegacyFormat = chunk.rich && !isWrappedVanna2;
        const hasSimple = chunk.simple && !chunk.rich;

        console.log('[CHUNK-REDUCER] Detection:', {
            isDirectVanna2,
            isWrappedVanna2,
            hasLegacyFormat,
            hasSimple,
            richType: chunk.rich?.type
        });

        if (isDirectVanna2) {
            console.log('[CHUNK-REDUCER] Processing as direct Vanna 2.0 component');
            this.processVanna2Component(chunk);
        } else if (isWrappedVanna2) {
            console.log('[CHUNK-REDUCER] Processing as wrapped Vanna 2.0 component (in rich)');
            this.processVanna2Component(chunk.rich as ChatStreamChunk);
        } else if (hasLegacyFormat) {
            console.log('[CHUNK-REDUCER] Processing as legacy rich format');
            this.processRichContent(chunk.rich);
        } else if (hasSimple) {
            console.log('[CHUNK-REDUCER] Processing as simple format');
            this.processSimpleContent(chunk.simple);
        } else {
            console.warn('[CHUNK-REDUCER] Unknown chunk format, storing as raw');
            // Unknown format - store as-is
            this.messageBuffer.content!.push({
                type: 'unknown',
                rawData: chunk,
                label: 'Unknown Chunk Format',
            });
        }

        return { ...this.messageBuffer };
    }

    /**
   * Process Vanna 2.0 component-based chunks
   */
    private processVanna2Component(chunk: ChatStreamChunk): void {
        // Infer type from structure if not provided
        const componentType = chunk.type || this.inferVanna2ComponentType(chunk);

        console.log('[CHUNK-REDUCER] Vanna2 component type:', componentType);
        console.log('[CHUNK-REDUCER] Is UI component?', this.uiComponentTypes.has(componentType));

        // Skip UI update types that should not be rendered
        if (this.uiComponentTypes.has(componentType)) {
            console.log('[CHUNK-REDUCER] ✅ FILTERED OUT:', componentType);
            return;
        }

        console.log('[CHUNK-REDUCER] Processing component type:', componentType);

        // Handle different component types
        switch (componentType) {
            case 'text':
            case 'simple_text':
            case 'markdown':
                // Text content - check multiple possible locations:
                // 1. chunk.text
                // 2. chunk.content
                // 3. chunk.data.content (nested structure)
                const textContent = chunk.text || chunk.content || chunk.data?.content || '';
                if (textContent) {
                    this.appendText(textContent);
                }
                break;

            case 'code':
            case 'sql':
                // Code content
                this.messageBuffer.content!.push({
                    type: 'code',
                    code: chunk.code || chunk.content || '',
                    language: chunk.language || 'sql',
                });
                break;

            case 'dataframe':
            case 'table':
                // Table content
                this.messageBuffer.content!.push({
                    type: 'dataframe',
                    data: chunk.data || [],
                    columns: chunk.columns || [],
                });
                break;

            case 'plotly':
            case 'chart':
                // Chart content - handles both flat and nested formats:
                // Flat: {type: 'plotly', data: [...], layout: {...}}
                // Nested: {type: 'plotly', data: {data: [...], layout: {...}}}
                let plotlyData = chunk.data;
                let plotlyLayout = chunk.layout;

                // Unwrap nested structure if data contains its own data/layout
                if (plotlyData && typeof plotlyData === 'object' && !Array.isArray(plotlyData) && 'data' in plotlyData) {
                    plotlyLayout = plotlyData.layout || plotlyLayout;
                    plotlyData = plotlyData.data;
                }

                this.messageBuffer.content!.push({
                    type: 'plotly',
                    data: plotlyData || [],
                    layout: plotlyLayout || {},
                });
                break;

            case 'tool_call':
                this.handleVanna2ToolCall(chunk);
                break;

            case 'tool_result':
                this.handleVanna2ToolResult(chunk);
                break;

            case 'thinking':
                this.handleThinking(chunk);
                break;

            case 'error':
                this.appendText(`\n\n⚠️ Error: ${chunk.description || chunk.content || 'Unknown error'}\n`);
                break;

            default:
                // Unknown component type - check if it has text content
                if (chunk.text || chunk.content) {
                    this.appendText(chunk.text || chunk.content || '');
                } else {
                    // Store as unknown for debugging
                    this.messageBuffer.content!.push({
                        type: 'unknown',
                        rawData: chunk,
                        label: chunk.title || componentType || 'Unknown Content',
                    });
                }
        }

        // Process children recursively
        if (chunk.children && Array.isArray(chunk.children)) {
            chunk.children.forEach(child => this.processVanna2Component(child as ChatStreamChunk));
        }
    }

    /**
     * Process rich content object from chunk (legacy format)
     */
    private processRichContent(rich: any): void {
        const type = rich.type || this.inferType(rich);

        switch (type) {
            case 'text':
            case 'markdown':
                this.appendText(rich.content || rich.text || '');
                break;

            case 'code':
            case 'sql':
                this.messageBuffer.content!.push({
                    type: 'code',
                    code: rich.code || rich.content || '',
                    language: rich.language || 'sql',
                });
                break;

            case 'dataframe':
            case 'table':
                this.messageBuffer.content!.push({
                    type: 'dataframe',
                    data: rich.data || [],
                    columns: rich.columns || [],
                });
                break;

            case 'plotly':
            case 'chart':
                this.messageBuffer.content!.push({
                    type: 'plotly',
                    data: rich.data || {},
                    layout: rich.layout || {},
                });
                break;

            case 'tool_call':
                this.handleToolCall(rich);
                break;

            case 'tool_result':
                this.handleToolResult(rich);
                break;

            case 'thinking':
                this.handleThinking(rich);
                break;

            case 'error':
                this.appendText(`\n\n⚠️ Error: ${rich.message || rich.error}\n`);
                break;

            default:
                // Unknown type - store as raw JSON for debugging
                this.messageBuffer.content!.push({
                    type: 'unknown',
                    rawData: rich,
                    label: type || 'Unknown Content',
                });
        }
    }

    /**
     * Process simple content (string or object) - legacy format
     */
    private processSimpleContent(simple: any): void {
        if (typeof simple === 'string') {
            this.appendText(simple);
        } else if (simple?.text) {
            this.appendText(simple.text);
        } else if (simple?.content) {
            this.appendText(simple.content);
        }
    }

    /**
     * Append text to the last text content block (or create new one)
     */
    private appendText(text: string): void {
        if (!text) return;

        const lastContent = this.messageBuffer.content![
            this.messageBuffer.content!.length - 1
        ];

        if (lastContent && lastContent.type === 'text') {
            // Append to existing text block
            lastContent.content += text;
        } else {
            // Create new text block
            this.messageBuffer.content!.push({
                type: 'text',
                content: text,
            });
        }
    }

    /**
     * Handle tool call event (Vanna 2.0)
     */
    private handleVanna2ToolCall(chunk: ChatStreamChunk): void {
        const toolCall: ToolExecution = {
            id: chunk.id || `tool-${Date.now()}`,
            name: chunk.title || 'unknown_tool',
            arguments: chunk.metadata || {},
            status: 'executing',
        };

        this.messageBuffer.toolCalls!.push(toolCall);
    }

    /**
     * Handle tool result event (Vanna 2.0)
     */
    private handleVanna2ToolResult(chunk: ChatStreamChunk): void {
        const toolId = chunk.id;
        const toolCall = this.messageBuffer.toolCalls!.find((t) => t.id === toolId);

        if (toolCall) {
            toolCall.status = chunk.status === 'error' ? 'error' : 'complete';
            toolCall.result = chunk.content || chunk.data;
            toolCall.error = chunk.status === 'error' ? chunk.description : undefined;
        }
    }

    /**
     * Handle tool call event (legacy format)
     */
    private handleToolCall(rich: any): void {
        const toolCall: ToolExecution = {
            id: rich.tool_id || rich.id || `tool-${Date.now()}`,
            name: rich.tool_name || rich.name || 'unknown_tool',
            arguments: rich.arguments || rich.args || {},
            status: 'executing',
        };

        this.messageBuffer.toolCalls!.push(toolCall);
    }

    /**
     * Handle tool result event (legacy format)
     */
    private handleToolResult(rich: any): void {
        const toolId = rich.tool_id || rich.id;
        const toolCall = this.messageBuffer.toolCalls!.find((t) => t.id === toolId);

        if (toolCall) {
            toolCall.status = rich.error ? 'error' : 'complete';
            toolCall.result = rich.result || rich.output;
            toolCall.duration = rich.duration || rich.elapsed_time;
            toolCall.error = rich.error;
        } else {
            console.warn('[CHUNK-REDUCER] Received tool result for unknown tool ID:', toolId);
        }
    }

    /**
     * Handle thinking/reasoning steps
     */
    private handleThinking(data: any): void {
        if (!this.messageBuffer.thinking) {
            this.messageBuffer.thinking = [];
        }

        if (data.steps && Array.isArray(data.steps)) {
            this.messageBuffer.thinking.push(...data.steps);
        } else if (data.step || data.description) {
            this.messageBuffer.thinking.push({
                step: this.messageBuffer.thinking.length + 1,
                description: data.step || data.description || '',
                status: data.status || 'in-progress',
            });
        }
    }

    /**
     * Infer Vanna 2.0 component type from structure
     */
    private inferVanna2ComponentType(chunk: any): string {
        // RichTextComponent: has 'content' and 'markdown' fields, no 'type'
        if ('content' in chunk && 'markdown' in chunk && !('type' in chunk)) {
            console.log('[CHUNK-REDUCER] Inferred type: text (RichTextComponent detected)');
            return 'text';
        }

        // StatusCardComponent: has 'title', 'status'
        if ('title' in chunk && 'status' in chunk) {
            console.log('[CHUNK-REDUCER] Inferred type: status_card');
            return 'status_card';
        }

        // CodeComponent: has 'code' and 'language'
        if ('code' in chunk && 'language' in chunk) {
            console.log('[CHUNK-REDUCER] Inferred type: code');
            return 'code';
        }

        // DataFrameComponent: has 'data' and 'columns'
        if ('data' in chunk && 'columns' in chunk && Array.isArray(chunk.data)) {
            console.log('[CHUNK-REDUCER] Inferred type: dataframe');
            return 'dataframe';
        }

        // PlotlyComponent: has 'data' and 'layout'
        if ('data' in chunk && 'layout' in chunk && !Array.isArray(chunk.data)) {
            console.log('[CHUNK-REDUCER] Inferred type: plotly');
            return 'plotly';
        }

        console.log('[CHUNK-REDUCER] Could not infer type, defaulting to unknown');
        return 'unknown';
    }

    /**
     * Infer content type from structure (legacy format)
     */
    private inferType(rich: any): string {
        if (rich.code || rich.sql) return 'code';
        if (rich.data && Array.isArray(rich.data) && rich.columns) return 'dataframe';
        if (rich.data && rich.layout) return 'plotly';
        if (rich.tool_name || rich.tool_id) return 'tool_call';
        if (rich.result || rich.output) return 'tool_result';
        if (rich.steps || rich.step) return 'thinking';
        if (rich.error || rich.message) return 'error';
        if (rich.text || rich.content) return 'text';
        return 'unknown';
    }

    /**
     * Get the complete assembled message
     */
    getCompleteMessage(): AssistantMessage {
        return this.messageBuffer as AssistantMessage;
    }

    /**
     * Reset the reducer for a new message
     */
    reset(): void {
        this.messageBuffer = {
            id: '',
            role: 'assistant',
            content: [],
            metadata: {},
            toolCalls: [],
            timestamp: Date.now(),
        };
    }
}
