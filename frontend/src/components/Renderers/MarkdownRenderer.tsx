import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface Props {
    content: string;
    className?: string;
}

/**
 * Markdown Renderer Component
 * 
 * Renders markdown with GitHub Flavored Markdown support
 * Includes syntax highlighting for code blocks
 * Handles image paths (proxies local paths through backend)
 */
export default function MarkdownRenderer({ content, className = '' }: Props) {
    const convertImagePath = (src: string | undefined): string => {
        if (!src) return '';

        // If it's a local file path (starts with / or contains .csv filename), proxy through backend
        if (src.startsWith('/') || src.includes('.png') || src.includes('.jpg') || src.includes('.jpeg') || src.includes('.svg')) {
            // Extract just the filename
            const filename = src.split('/').pop() || src;
            // Proxy through backend file serving endpoint
            return `/api/files/${filename}`;
        }

        return src;
    };

    return (
        <div className={`markdown-content ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                    // Custom link rendering to open in new tab
                    a: ({ node, ...props }) => (
                        <a {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                    // Custom image rendering to proxy local paths
                    img: ({ node, src, alt, ...props }) => {
                        const proxiedSrc = convertImagePath(src);
                        console.log('[MARKDOWN] Image src:', src, '→', proxiedSrc);
                        return (
                            <img
                                {...props}
                                src={proxiedSrc}
                                alt={alt || ''}
                                className="max-w-full h-auto rounded-lg shadow-md my-4"
                                onError={(e) => {
                                    console.error('[MARKDOWN] Image failed to load:', proxiedSrc);
                                    // Show alt text on error
                                    e.currentTarget.style.display = 'none';
                                    const wrapper = e.currentTarget.parentElement;
                                    if (wrapper) {
                                        wrapper.innerHTML = `<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 my-4">
                                            <p class="text-yellow-800"><strong>Image not available:</strong> ${alt || 'Unknown'}</p>
                                            <p class="text-sm text-yellow-600 mt-1">Path: ${src}</p>
                                        </div>`;
                                    }
                                }}
                            />
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
