import type { MessageContent } from '@/types';
import MarkdownRenderer from './MarkdownRenderer';
import CodeBlock from './CodeBlock';
import DataTable from './DataTable';
import PlotlyChart from './PlotlyChart';
import RawJsonViewer from './RawJsonViewer';

interface Props {
    content: MessageContent[];
}

/**
 * MessageRenderer Component
 * 
 * Routes message content to appropriate renderer based on type
 * Handles all content types: text, code, dataframe, plotly, unknown
 */
export default function MessageRenderer({ content }: Props) {
    if (!content || content.length === 0) {
        return null;
    }

    return (
        <div className="space-y-3">
            {content.map((item, index) => (
                <ContentItem key={index} content={item} />
            ))}
        </div>
    );
}

function ContentItem({ content }: { content: MessageContent }) {
    switch (content.type) {
        case 'text':
            return <MarkdownRenderer content={content.content} />;

        case 'code':
            return <CodeBlock code={content.code} language={content.language} />;

        case 'dataframe':
            return <DataTable data={content.data} columns={content.columns} />;

        case 'plotly':
            return <PlotlyChart data={content.data} layout={content.layout} />;

        case 'unknown':
            return <RawJsonViewer data={content.rawData} label={content.label} />;

        default:
            // Type safety: this should never happen
            console.warn('Unknown content type:', content);
            return <RawJsonViewer data={content} label="Unhandled Type" />;
    }
}
