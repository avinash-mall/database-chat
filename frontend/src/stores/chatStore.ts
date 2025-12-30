import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatState, Conversation, Message, AssistantMessage, UserMessage } from '@/types';

interface ChatStore extends ChatState {
    // Actions
    createConversation: (title?: string) => string;
    setActiveConversation: (id: string | null) => void;
    addMessage: (conversationId: string, message: Message) => void;
    addUserMessage: (conversationId: string, content: string) => UserMessage;
    updateStreamingMessage: (message: Partial<AssistantMessage>) => void;
    completeStreamingMessage: (message: AssistantMessage) => void;
    setStreaming: (isStreaming: boolean) => void;
    clearConversation: (id: string) => void;
    deleteConversation: (id: string) => void;
    setConnectionStatus: (status: ChatState['connectionStatus']) => void;
    setStreamingStatus: (status: ChatState['streamingStatus']) => void;
}

/**
 * Zustand store for chat state
 * Manages conversations, messages, and streaming state
 */
export const useChatStore = create<ChatStore>()(
    persist(
        (set, get) => ({
            conversations: {},
            activeConversationId: null,
            isStreaming: false,
            currentStreamingMessage: null,
            connectionStatus: 'disconnected',
            streamingStatus: 'idle',

            createConversation: (title = 'New Chat') => {
                const id = `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                const conversation: Conversation = {
                    id,
                    title,
                    messages: [],
                    createdAt: Date.now(),
                    updatedAt: Date.now(),
                };

                set((state) => ({
                    conversations: {
                        ...state.conversations,
                        [id]: conversation,
                    },
                    activeConversationId: id,
                }));

                return id;
            },

            setActiveConversation: (id) => {
                set({ activeConversationId: id });
            },

            addMessage: (conversationId, message) => {
                set((state) => {
                    const conversation = state.conversations[conversationId];
                    if (!conversation) return state;

                    return {
                        conversations: {
                            ...state.conversations,
                            [conversationId]: {
                                ...conversation,
                                messages: [...conversation.messages, message],
                                updatedAt: Date.now(),
                            },
                        },
                    };
                });
            },

            addUserMessage: (conversationId, content) => {
                const message: UserMessage = {
                    id: `msg-${Date.now()}`,
                    role: 'user',
                    content,
                    timestamp: Date.now(),
                };

                get().addMessage(conversationId, message);
                return message;
            },

            updateStreamingMessage: (message) => {
                set({ currentStreamingMessage: message });
            },

            completeStreamingMessage: (message) => {
                const { activeConversationId } = get();
                if (activeConversationId) {
                    get().addMessage(activeConversationId, message);
                }
                set({
                    currentStreamingMessage: null,
                    isStreaming: false,
                    streamingStatus: 'complete',
                });
            },

            setStreaming: (isStreaming) => {
                set({
                    isStreaming,
                    streamingStatus: isStreaming ? 'streaming' : 'idle',
                });
            },

            clearConversation: (id) => {
                set((state) => {
                    const conversation = state.conversations[id];
                    if (!conversation) return state;

                    return {
                        conversations: {
                            ...state.conversations,
                            [id]: {
                                ...conversation,
                                messages: [],
                                updatedAt: Date.now(),
                            },
                        },
                    };
                });
            },

            deleteConversation: (id) => {
                set((state) => {
                    const { [id]: deleted, ...rest } = state.conversations;
                    return {
                        conversations: rest,
                        activeConversationId:
                            state.activeConversationId === id ? null : state.activeConversationId,
                    };
                });
            },

            setConnectionStatus: (status) => {
                set({ connectionStatus: status });
            },

            setStreamingStatus: (status) => {
                set({ streamingStatus: status });
            },
        }),
        {
            name: 'chat-storage',
            partialize: (state) => ({
                conversations: state.conversations,
                activeConversationId: state.activeConversationId,
            }),
        }
    )
);
