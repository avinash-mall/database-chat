import { useState } from 'react';
import toast from 'react-hot-toast';
import type { AssistantMessage as AssistantMessageType } from '@/types';
import MessageRenderer from '../Renderers/MessageRenderer';
import ToolTracePanel from './ToolTracePanel';

interface Props {
    message: AssistantMessageType | Partial<AssistantMessageType>;
    isStreaming?: boolean;
}

/**
 * AssistantMessage Component
 * 
 * Displays AI assistant message with:
 * - Rich content rendering
 * - Tool execution traces
 * - Copy functionality
 * - Streaming animation
 */
export default function AssistantMessage({ message, isStreaming = false }: Props) {
    const [copied, setCopied] = useState(false);

    const timeString = message.timestamp
        ? new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
        })
        : '';

    const handleCopy = async () => {
        try {
            const textContent = message.content
                ?.filter((c) => c.type === 'text')
                .map((c) => (c.type === 'text' ? c.content : ''))
                .join('\n');

            await navigator.clipboard.writeText(textContent || '');
            setCopied(true);
            toast.success('Message copied!');
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            toast.error('Failed to copy message');
        }
    };

    return (
        <div className="flex justify-start mb-4 animate-slide-in">
            <div className="max-w-4xl w-full">
                {/* AI Avatar & Content */}
                <div className="flex gap-3">
                    {/* Avatar */}
                    <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-vanna-teal to-vanna-navy flex items-center justify-center text-white font-bold text-sm">
                            AI
                        </div>
                    </div>

                    {/* Message Content */}
                    <div className="flex-1 min-w-0">
                        <div className="bg-white rounded-2xl rounded-tl-sm px-5 py-4 shadow-md border border-gray-200">
                            {/* Streaming indicator */}
                            {isStreaming && (
                                <div className="flex items-center gap-2 mb-3 text-vanna-teal text-sm">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-vanna-teal rounded-full animate-pulse"></span>
                                        <span className="w-2 h-2 bg-vanna-teal rounded-full animate-pulse [animation-delay:0.2s]"></span>
                                        <span className="w-2 h-2 bg-vanna-teal rounded-full animate-pulse [animation-delay:0.4s]"></span>
                                    </div>
                                    <span>Generating response...</span>
                                </div>
                            )}

                            {/* Message content */}
                            {message.content && message.content.length > 0 && (
                                <MessageRenderer content={message.content} />
                            )}

                            {/* Tool traces */}
                            {message.toolCalls && message.toolCalls.length > 0 && (
                                <div className="mt-4">
                                    <ToolTracePanel toolCalls={message.toolCalls} />
                                </div>
                            )}
                        </div>

                        {/* Actions & Timestamp */}
                        <div className="flex items-center justify-between mt-1 px-1">
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleCopy}
                                    className="text-xs text-gray-500 hover:text-vanna-teal transition flex items-center gap-1"
                                    title="Copy message"
                                >
                                    {copied ? (
                                        <>
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                            Copied
                                        </>
                                    ) : (
                                        <>
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                            </svg>
                                            Copy
                                        </>
                                    )}
                                </button>
                            </div>
                            {timeString && <span className="text-xs text-gray-500">{timeString}</span>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
