import { useEffect } from 'react';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/stores/authStore';
import { useChatStore } from '@/stores/chatStore';
import { useChatStream } from '@/hooks/useChatStream';
import { apiClient } from '@/services/api-client';
import MessageList from '@/components/Chat/MessageList';
import ChatInput from '@/components/Chat/ChatInput';

/**
 * ChatLayout Component
 * 
 * Main chat interface with:
 * - Message history
 * - Streaming responses
 * - User input
 * - Header with user info
 */
export default function ChatLayout() {
    const { user, clearAuth } = useAuthStore();
    const {
        conversations,
        activeConversationId,
        createConversation,
        addUserMessage,
        setStreaming,
        currentStreamingMessage,
        isStreaming,
    } = useChatStore();

    const { sendMessage, currentMessage, error } = useChatStream(activeConversationId);

    // Create initial conversation if none exists
    useEffect(() => {
        if (!activeConversationId) {
            createConversation('New Chat');
        }
    }, [activeConversationId, createConversation]);

    // Show streaming error
    useEffect(() => {
        if (error) {
            toast.error(error);
        }
    }, [error]);

    // Update streaming state in store
    useEffect(() => {
        if (currentMessage) {
            useChatStore.setState({ currentStreamingMessage: currentMessage });
        }
    }, [currentMessage]);

    const handleLogout = () => {
        apiClient.logout();
        clearAuth();
    };

    const handleNewChat = () => {
        if (window.confirm('Start a new conversation? This will clear all messages.')) {
            // Clear all conversations and create a new one
            useChatStore.setState({ conversations: {}, activeConversationId: null });
            createConversation('New Chat');
        }
    };

    const handleSendMessage = async (messageText: string) => {
        if (!activeConversationId || !messageText.trim()) return;

        // Add user message to conversation
        addUserMessage(activeConversationId, messageText);

        // Start streaming
        setStreaming(true);

        try {
            await sendMessage(messageText, (finalMessage) => {
                // Complete the message
                useChatStore.getState().completeStreamingMessage(finalMessage);
            });
        } catch (err) {
            console.error('Send message error:', err);
            toast.error('Failed to send message');
            setStreaming(false);
        }
    };

    const activeConversation = activeConversationId
        ? conversations[activeConversationId]
        : null;

    return (
        <div className="min-h-screen flex flex-col bg-gradient-to-b from-vanna-cream to-white">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 shadow-sm flex-shrink-0">
                <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-vanna-navy font-serif">
                            Database Chat AI
                        </h1>
                        <p className="text-sm text-gray-600">
                            Interactive AI Assistant for Database Queries
                        </p>
                    </div>

                    <div className="flex items-center space-x-4">
                        {/* User info */}
                        <div className="text-right">
                            <p className="text-sm font-medium text-gray-900">
                                {user?.username}
                            </p>
                            <p className="text-xs text-gray-500">
                                {user?.groups.join(', ')}
                            </p>
                        </div>

                        {/* New Chat button */}
                        <button
                            onClick={handleNewChat}
                            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition text-sm font-medium flex items-center gap-1"
                            title="Start a new conversation"
                        >
                            <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 4v16m8-8H4"
                                />
                            </svg>
                            New Chat
                        </button>

                        {/* Logout button */}
                        <button
                            onClick={handleLogout}
                            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition text-sm font-medium"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Chat Container */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Messages */}
                <MessageList
                    messages={activeConversation?.messages || []}
                    currentStreamingMessage={currentStreamingMessage}
                    isStreaming={isStreaming}
                />

                {/* Input */}
                <ChatInput
                    onSend={handleSendMessage}
                    disabled={isStreaming}
                    placeholder={
                        isStreaming
                            ? 'Waiting for response...'
                            : 'Type your message... (Shift+Enter for new line)'
                    }
                />
            </div>

            {/* Connection status badge (optional) */}
            <div className="fixed bottom-20 right-4">
                <div className="bg-white shadow-lg rounded-lg px-3 py-2 flex items-center gap-2 border border-gray-200">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs text-gray-600 font-medium">Connected</span>
                </div>
            </div>
        </div>
    );
}
