import { useState, useCallback, useRef } from 'react';
import { apiClient } from '@/services/api-client';
import { ChunkReducer } from '@/utils/chunk-reducer';
import type { AssistantMessage, ChatStreamChunk } from '@/types';

/**
 * Custom hook for managing streaming chat with SSE
 * 
 * Features:
 * - Automatic chunk assembly
 * - Stream cancellation
 * - Error handling
 * - Progress tracking
 */
export function useChatStream(conversationId: string | null) {
    const [isStreaming, setIsStreaming] = useState(false);
    const [currentMessage, setCurrentMessage] = useState<Partial<AssistantMessage> | null>(null);
    const [error, setError] = useState<string | null>(null);

    const abortControllerRef = useRef<AbortController | null>(null);
    const chunkReducerRef = useRef<ChunkReducer>(new ChunkReducer());

    /**
     * Send a message via SSE streaming
     */
    const sendMessage = useCallback(
        async (
            userMessage: string,
            onMessageComplete: (message: AssistantMessage) => void
        ) => {
            // Reset state
            setIsStreaming(true);
            setCurrentMessage(null);
            setError(null);
            chunkReducerRef.current.reset();

            // Chunk handler
            const onChunk = (chunk: ChatStreamChunk) => {
                const updatedMessage = chunkReducerRef.current.processChunk(chunk);
                setCurrentMessage(updatedMessage);
            };

            // Completion handler
            const onComplete = () => {
                setIsStreaming(false);
                const finalMessage = chunkReducerRef.current.getCompleteMessage();
                setCurrentMessage(null);
                onMessageComplete(finalMessage);
            };

            // Error handler
            const onError = (err: Error) => {
                setIsStreaming(false);
                setCurrentMessage(null);
                setError(err.message);
                console.error('Streaming error:', err);
            };

            try {
                abortControllerRef.current = await apiClient.chatSSE(
                    userMessage,
                    conversationId,
                    onChunk,
                    onComplete,
                    onError
                );
            } catch (err) {
                onError(err as Error);
            }
        },
        [conversationId]
    );

    /**
     * Cancel the current stream
     */
    const cancelStream = useCallback(() => {
        abortControllerRef.current?.abort();
        setIsStreaming(false);
        setCurrentMessage(null);
        setError(null);
    }, []);

    return {
        sendMessage,
        cancelStream,
        isStreaming,
        currentMessage,
        error,
    };
}
