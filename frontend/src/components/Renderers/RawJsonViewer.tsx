import { useState } from 'react';

interface Props {
    data: any;
    label: string;
}

/**
 * RawJsonViewer Component
 * 
 * Fallback renderer for unknown content types
 * Shows expandable/collapsible JSON with syntax highlighting
 */
export default function RawJsonViewer({ data, label }: Props) {
    const [expanded, setExpanded] = useState(false);

    const jsonString = JSON.stringify(data, null, 2);
    const preview = JSON.stringify(data).slice(0, 100) + (JSON.stringify(data).length > 100 ? '...' : '');

    return (
        <div className="my-4 bg-yellow-50 border border-yellow-200 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="bg-yellow-100 px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span className="font-medium text-yellow-800">Unknown Content Type: {label}</span>
                </div>
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="text-sm text-yellow-700 hover:text-yellow-900 transition font-medium flex items-center gap-1"
                >
                    {expanded ? (
                        <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                            </svg>
                            Collapse
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                            Expand
                        </>
                    )}
                </button>
            </div>

            {/* Content */}
            <div className="p-4">
                {expanded ? (
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono">
                        {jsonString}
                    </pre>
                ) : (
                    <p className="text-gray-700 text-sm font-mono">
                        {preview}
                    </p>
                )}
            </div>

            {/* Debug info */}
            <div className="px-4 pb-3 text-xs text-yellow-700">
                💡 This content type is not yet supported. Raw data is shown for debugging.
            </div>
        </div>
    );
}
