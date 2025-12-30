import { useState } from 'react';
import type { ToolExecution } from '@/types';

interface Props {
    toolCalls: ToolExecution[];
}

/**
 * ToolTracePanel Component
 * 
 * Displays tool execution history with:
 * - Collapsible accordion
 * - Tool status indicators
 * - Input/output display
 * - Execution timing
 */
export default function ToolTracePanel({ toolCalls }: Props) {
    const [expanded, setExpanded] = useState(false);

    if (!toolCalls || toolCalls.length === 0) {
        return null;
    }

    const completedTools = toolCalls.filter((t) => t.status === 'complete').length;
    const errorTools = toolCalls.filter((t) => t.status === 'error').length;

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100 transition"
            >
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span className="font-medium text-gray-700">
                        Tools Used ({toolCalls.length})
                    </span>
                    {errorTools > 0 && (
                        <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded">
                            {errorTools} failed
                        </span>
                    )}
                </div>
                <svg
                    className={`w-5 h-5 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {/* Tool List */}
            {expanded && (
                <div className="border-t border-gray-200 divide-y divide-gray-200">
                    {toolCalls.map((tool, index) => (
                        <ToolExecutionCard key={tool.id || index} tool={tool} />
                    ))}
                </div>
            )}
        </div>
    );
}

function ToolExecutionCard({ tool }: { tool: ToolExecution }) {
    const [showDetails, setShowDetails] = useState(false);

    const statusIcon = {
        executing: (
            <div className="w-5 h-5 border-2 border-vanna-teal border-t-transparent rounded-full animate-spin"></div>
        ),
        complete: (
            <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
        ),
        error: (
            <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
        ),
    };

    return (
        <div className="bg-white">
            <button
                onClick={() => setShowDetails(!showDetails)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition text-left"
            >
                <div className="flex items-center gap-3 flex-1">
                    {statusIcon[tool.status]}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-medium text-gray-900">{tool.name}</span>
                            {tool.duration && (
                                <span className="text-xs text-gray-500">{tool.duration.toFixed(2)}s</span>
                            )}
                        </div>
                        {tool.error && (
                            <p className="text-xs text-red-600 mt-1">{tool.error}</p>
                        )}
                    </div>
                </div>
                <svg
                    className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${showDetails ? 'rotate-90' : ''
                        }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
            </button>

            {showDetails && (
                <div className="px-4 pb-4 space-y-3 border-t border-gray-100 bg-gray-50">
                    {/* Arguments */}
                    {tool.arguments && Object.keys(tool.arguments).length > 0 && (
                        <div>
                            <p className="text-xs font-medium text-gray-600 mb-1">Input:</p>
                            <pre className="text-xs bg-white border border-gray-200 rounded p-2 overflow-x-auto">
                                {JSON.stringify(tool.arguments, null, 2)}
                            </pre>
                        </div>
                    )}

                    {/* Result */}
                    {tool.result && (
                        <div>
                            <p className="text-xs font-medium text-gray-600 mb-1">Output:</p>
                            <pre className="text-xs bg-white border border-gray-200 rounded p-2 overflow-x-auto max-h-48">
                                {typeof tool.result === 'string'
                                    ? tool.result
                                    : JSON.stringify(tool.result, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
