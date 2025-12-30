import { useEffect, useRef } from 'react';
import type { Message, AssistantMessage as AssistantMessageType } from '@/types';
import UserMessage from './UserMessage';
import AssistantMessage from './AssistantMessage';

interface Props {
    messages: Message[];
    currentStreamingMessage?: Partial<AssistantMessageType> | null;
    isStreaming?: boolean;
}

/**
 * MessageList Component
 * 
 * Displays conversation messages with:
 * - Auto-scroll to bottom
 * - Streaming message display
 * - Empty state
 * - Scroll-to-bottom button
 */
export default function MessageList({
    messages,
    currentStreamingMessage,
    isStreaming = false,
}: Props) {
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, currentStreamingMessage]);

    if (messages.length === 0 && !currentStreamingMessage) {
        return (
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center max-w-md">
                    <div className="inline-block p-4 bg-vanna-teal/10 rounded-full mb-4">
                        <svg
                            className="w-16 h-16 text-vanna-teal"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                            />
                        </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                        Start a Conversation
                    </h3>
                    <p className="text-gray-600 mb-6">
                        Ask me anything about your database. I can help you write SQL queries,
                        analyze data, and visualize results.
                    </p>
                    <div className="space-y-2 text-sm text-left">
                        <p className="text-gray-700">
                            <strong>Try asking:</strong>
                        </p>
                        <ul className="space-y-1 text-gray-600">
                            <li>• "Show me all employees in the sales department"</li>
                            <li>• "What are the top 10 products by revenue?"</li>
                            <li>• "Create a chart of monthly sales trends"</li>
                        </ul>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="flex-1 overflow-y-auto px-4 py-6"
            style={{ scrollBehavior: 'smooth' }}
        >
            <div className="max-w-5xl mx-auto space-y-4">
                {/* Existing messages */}
                {messages.map((message) => {
                    if (message.role === 'user') {
                        return <UserMessage key={message.id} message={message} />;
                    } else if (message.role === 'assistant') {
                        return (
                            <AssistantMessage
                                key={message.id}
                                message={message as AssistantMessageType}
                            />
                        );
                    } else if (message.role === 'error') {
                        return (
                            <div
                                key={message.id}
                                className="bg-red-50 border border-red-200 rounded-lg p-4 my-4"
                            >
                                <div className="flex items-start gap-3">
                                    <svg
                                        className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        />
                                    </svg>
                                    <div className="flex-1">
                                        <p className="font-medium text-red-800">Error</p>
                                        <p className="text-sm text-red-700 mt-1">{message.error}</p>
                                        {message.details && (
                                            <p className="text-xs text-red-600 mt-2 font-mono">
                                                {message.details}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    }
                    return null;
                })}

                {/* Streaming message */}
                {currentStreamingMessage && (
                    <AssistantMessage
                        message={currentStreamingMessage}
                        isStreaming={isStreaming}
                    />
                )}

                {/* Scroll anchor */}
                <div ref={messagesEndRef} />
            </div>
        </div>
    );
}
