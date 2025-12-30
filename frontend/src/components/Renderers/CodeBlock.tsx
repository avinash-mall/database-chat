import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import toast from 'react-hot-toast';

interface Props {
    code: string;
    language: string;
    showLineNumbers?: boolean;
}

/**
 * CodeBlock Component
 * 
 * Displays syntax-highlighted code with copy functionality
 * Supports SQL and other languages
 */
export default function CodeBlock({ code, language, showLineNumbers = true }: Props) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            toast.success('Code copied to clipboard!');
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            toast.error('Failed to copy code');
        }
    };

    return (
        <div className="relative group my-4">
            {/* Language label */}
            <div className="flex items-center justify-between bg-gray-800 text-gray-300 px-4 py-2 rounded-t-lg text-sm">
                <span className="font-mono uppercase">{language}</span>
                <button
                    onClick={handleCopy}
                    className="flex items-center gap-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded transition text-xs"
                    title="Copy code"
                >
                    {copied ? (
                        <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            Copied!
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            Copy
                        </>
                    )}
                </button>
            </div>

            {/* Code block */}
            <SyntaxHighlighter
                language={language.toLowerCase()}
                style={vscDarkPlus}
                showLineNumbers={showLineNumbers}
                customStyle={{
                    margin: 0,
                    borderTopLeftRadius: 0,
                    borderTopRightRadius: 0,
                    borderBottomLeftRadius: '0.5rem',
                    borderBottomRightRadius: '0.5rem',
                }}
                codeTagProps={{
                    style: {
                        fontFamily: 'Space Mono, ui-monospace, monospace',
                        fontSize: '0.875rem',
                    },
                }}
            >
                {code}
            </SyntaxHighlighter>
        </div>
    );
}
