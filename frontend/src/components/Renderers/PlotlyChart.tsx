import Plot from 'react-plotly.js';

interface Props {
    data: any;
    layout?: any;
    config?: any;
}

/**
 * PlotlyChart Component
 * 
 * Renders interactive Plotly charts
 * Supports all Plotly chart types
 * Handles binary data decoding (bdata format)
 */
export default function PlotlyChart({ data, layout = {}, config = {} }: Props) {
    /**
     * Decode binary data format used by Vanna backend
     * Plotly data may come with {bdata: "base64string", dtype: "i1"} instead of numeric arrays
     */
    const decodeBinaryData = (obj: any): any => {
        if (!obj) return obj;

        // Handle arrays
        if (Array.isArray(obj)) {
            return obj.map(item => decodeBinaryData(item));
        }

        // Handle objects
        if (typeof obj === 'object') {
            // Check if this is a binary data object
            if (obj.bdata && obj.dtype) {
                try {
                    // Decode base64 to binary
                    const binaryString = atob(obj.bdata);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }

                    // Convert based on dtype
                    // i1 = int8, f4 = float32, f8 = float64
                    switch (obj.dtype) {
                        case 'i1': // int8
                            return Array.from(new Int8Array(bytes.buffer));
                        case 'i2': // int16
                            return Array.from(new Int16Array(bytes.buffer));
                        case 'i4': // int32
                            return Array.from(new Int32Array(bytes.buffer));
                        case 'f4': // float32
                            return Array.from(new Float32Array(bytes.buffer));
                        case 'f8': // float64
                            return Array.from(new Float64Array(bytes.buffer));
                        default:
                            console.warn('Unknown dtype:', obj.dtype);
                            return Array.from(bytes);
                    }
                } catch (error) {
                    console.error('Failed to decode binary data:', error);
                    return obj;
                }
            }

            // Recursively decode nested objects
            const decoded: any = {};
            for (const key in obj) {
                decoded[key] = decodeBinaryData(obj[key]);
            }
            return decoded;
        }

        return obj;
    };

    // Decode binary data in traces
    const decodedData = decodeBinaryData(data);

    const defaultLayout = {
        autosize: true,
        margin: { l: 50, r: 50, t: 50, b: 50 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            family: 'Space Grotesk, sans-serif',
            size: 12,
            color: '#374151',
        },
        ...layout,
    };

    const defaultConfig = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        toImageButtonOptions: {
            format: 'png',
            filename: 'chart',
            height: 800,
            width: 1200,
            scale: 2,
        },
        ...config,
    };

    try {
        return (
            <div className="my-4 bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                <Plot
                    data={Array.isArray(decodedData) ? decodedData : [decodedData]}
                    layout={defaultLayout}
                    config={defaultConfig}
                    className="w-full"
                    useResizeHandler
                    style={{ width: '100%', height: '400px' }}
                />
            </div>
        );
    } catch (error) {
        console.error('Plotly rendering error:', error);
        return (
            <div className="my-4 bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700 font-medium">Failed to render chart</p>
                <p className="text-red-600 text-sm mt-1">
                    {error instanceof Error ? error.message : 'Unknown error'}
                </p>
            </div>
        );
    }
}
