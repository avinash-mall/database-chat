import type { UserMessage as UserMessageType } from '@/types';

interface Props {
    message: UserMessageType;
}

/**
 * UserMessage Component
 * 
 * Displays user message bubble with timestamp
 */
export default function UserMessage({ message }: Props) {
    const timeString = new Date(message.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
    });

    return (
        <div className="flex justify-end mb-4 animate-slide-in">
            <div className="max-w-3xl">
                <div className="bg-vanna-teal text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-md">
                    <p className="text-base whitespace-pre-wrap break-words">{message.content}</p>
                </div>
                <div className="text-right mt-1">
                    <span className="text-xs text-gray-500">{timeString}</span>
                </div>
            </div>
        </div>
    );
}
