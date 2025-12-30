import { useState, useMemo } from 'react';

interface Props {
    data: any[];
    columns: string[];
    maxRows?: number;
}

type SortDirection = 'asc' | 'desc' | null;

/**
 * DataTable Component
 * 
 * Displays tabular data with:
 * - Column sorting
 * - Row limiting with "show more"
 * - Responsive design
 */
export default function DataTable({ data, columns, maxRows = 10 }: Props) {
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<SortDirection>(null);
    const [showAll, setShowAll] = useState(false);

    // Sort data
    const sortedData = useMemo(() => {
        if (!sortColumn || !sortDirection) return data;

        return [...data].sort((a, b) => {
            const aVal = a[sortColumn];
            const bVal = b[sortColumn];

            if (aVal === bVal) return 0;
            if (aVal == null) return 1;
            if (bVal == null) return -1;

            const compare = aVal < bVal ? -1 : 1;
            return sortDirection === 'asc' ? compare : -compare;
        });
    }, [data, sortColumn, sortDirection]);

    // Limit rows
    const displayData = showAll ? sortedData : sortedData.slice(0, maxRows);

    const handleSort = (column: string) => {
        if (sortColumn === column) {
            // Cycle through: asc -> desc -> null
            setSortDirection(
                sortDirection === 'asc' ? 'desc' : sortDirection === 'desc' ? null : 'asc'
            );
            if (sortDirection === 'desc') setSortColumn(null);
        } else {
            setSortColumn(column);
            setSortDirection('asc');
        }
    };

    if (!data || data.length === 0) {
        return (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
                No data to display
            </div>
        );
    }

    return (
        <div className="my-4">
            <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            {columns.map((column) => (
                                <th
                                    key={column}
                                    onClick={() => handleSort(column)}
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition select-none"
                                >
                                    <div className="flex items-center gap-2">
                                        <span>{column}</span>
                                        {sortColumn === column && (
                                            <span className="text-vanna-teal">
                                                {sortDirection === 'asc' ? '↑' : '↓'}
                                            </span>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {displayData.map((row, idx) => (
                            <tr key={idx} className="hover:bg-gray-50 transition">
                                {columns.map((column) => (
                                    <td
                                        key={column}
                                        className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                                    >
                                        {row[column] != null ? String(row[column]) : <span className="text-gray-400">—</span>}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Show more/less button */}
            {data.length > maxRows && (
                <div className="mt-3 text-center">
                    <button
                        onClick={() => setShowAll(!showAll)}
                        className="px-4 py-2 text-sm text-vanna-teal hover:text-vanna-navy transition font-medium"
                    >
                        {showAll ? (
                            <>Show Less ({data.length - maxRows} hidden)</>
                        ) : (
                            <>Show All ({data.length - maxRows} more rows)</>
                        )}
                    </button>
                </div>
            )}

            {/* Row count */}
            <p className="mt-2 text-xs text-gray-500 text-center">
                Showing {displayData.length} of {data.length} rows
            </p>
        </div>
    );
}
