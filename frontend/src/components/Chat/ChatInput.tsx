import { useState, useRef, useEffect, KeyboardEvent } from 'react';

interface Props {
    onSend: (message: string) => void;
    disabled?: boolean;
    placeholder?: string;
}

/**
 * ChatInput Component
 * 
 * Message input with:
 * - Auto-resize textarea
 * - Enter to send / Shift+Enter for newline
 * - Character counter
 * - Send button
 */
export default function ChatInput({
    onSend,
    disabled = false,
    placeholder = 'Type your message... (Shift+Enter for new line)',
}: Props) {
    const [message, setMessage] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [message]);

    const handleSend = () => {
        const trimmed = message.trim();
        if (!trimmed || disabled) return;

        onSend(trimmed);
        setMessage('');

        // Reset height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="border-t border-gray-200 bg-white p-4">
            <div className="max-w-4xl mx-auto">
                <div className="flex gap-3 items-end">
                    {/* Textarea */}
                    <div className="flex-1 relative">
                        <textarea
                            ref={textareaRef}
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={placeholder}
                            disabled={disabled}
                            rows={1}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-vanna-teal focus:border-transparent transition resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                            style={{ maxHeight: '200px' }}
                        />

                        {/* Character counter */}
                        {message.length > 0 && (
                            <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                                {message.length}
                            </div>
                        )}
                    </div>

                    {/* Send button */}
                    <button
                        onClick={handleSend}
                        disabled={!message.trim() || disabled}
                        className="px-6 py-3 bg-vanna-teal text-white rounded-lg hover:bg-vanna-navy transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
                        title="Send message (Enter)"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                        Send
                    </button>
                </div>

                {/* Help text */}
                <p className="text-xs text-gray-500 mt-2">
                    Press <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">Enter</kbd> to send,{' '}
                    <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">Shift+Enter</kbd> for new line
                </p>
            </div>
        </div>
    );
}
