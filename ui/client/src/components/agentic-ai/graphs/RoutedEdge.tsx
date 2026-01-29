import React from "react";
import { EdgeProps } from "reactflow";
import { X } from "lucide-react";

/** Data payload for routed edges with smart routing information */
interface RoutedEdgeData {
  /** Points along the routed path */
  routedPoints?: { x: number; y: number }[];
  /** Optional label to display on the edge */
  label?: string;
  /** Whether this edge is part of a bidirectional pair */
  isBidirectional?: boolean;
  /** IDs of both edges in a bidirectional pair (for deletion) */
  bidirectionalEdgeIds?: string[];
  /** Delete handler passed via data */
  onDelete?: (edgeId: string) => void;
}

interface RoutedEdgeProps extends EdgeProps<RoutedEdgeData> {
  onDelete?: (edgeId: string) => void;
}

const RoutedEdge: React.FC<RoutedEdgeProps> = ({
  id,
  data,
  style = {},
  markerEnd,
  markerStart,
  onDelete,
}) => {
  const points = Array.isArray(data?.routedPoints) ? data.routedPoints : [];
  if (points.length < 2) {
    return null;
  }

  const pathD = points
    .map((point: { x: number; y: number }, index: number) =>
      index === 0 ? `M ${point.x},${point.y}` : `L ${point.x},${point.y}`,
    )
    .join(" ");

  const segmentLengths: number[] = [];
  let totalLength = 0;
  for (let i = 0; i < points.length - 1; i += 1) {
    const start = points[i];
    const end = points[i + 1];
    const length = Math.hypot(end.x - start.x, end.y - start.y);
    segmentLengths.push(length);
    totalLength += length;
  }

  const halfway = totalLength / 2;
  let walked = 0;
  let labelX = points[0].x;
  let labelY = points[0].y;
  for (let i = 0; i < segmentLengths.length; i += 1) {
    const length = segmentLengths[i];
    if (walked + length >= halfway) {
      const start = points[i];
      const end = points[i + 1];
      const remaining = halfway - walked;
      const ratio = length > 0 ? remaining / length : 0;
      labelX = start.x + (end.x - start.x) * ratio;
      labelY = start.y + (end.y - start.y) * ratio;
      break;
    }
    walked += length;
  }

  // Compute delete handler once before render to conditionally show delete button
  const deleteFunction = data?.onDelete || onDelete;

  const handleDelete = (event: React.MouseEvent) => {
    event.stopPropagation();
    if (deleteFunction) {
      const edgeIds = Array.isArray(data?.bidirectionalEdgeIds)
        ? data.bidirectionalEdgeIds
        : [id];
      edgeIds.forEach((edgeId: string) => deleteFunction(edgeId));
    }
  };

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={pathD}
        fill="none"
        markerEnd={markerEnd}
        markerStart={markerStart}
      />
      {deleteFunction && (
        <foreignObject
          width={20}
          height={20}
          x={labelX - 10}
          y={labelY - 10}
          className="edgebutton-foreignobject"
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div className="flex items-center justify-center">
            <button
              className="group opacity-0 hover:opacity-100 focus:opacity-100 transition-opacity duration-200 bg-red-600 hover:bg-red-700 focus:bg-red-700 text-white rounded-full w-5 h-5 flex items-center justify-center border border-red-500 shadow-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-1 focus:ring-offset-gray-800"
              onClick={handleDelete}
              title="Delete edge"
              aria-label="Delete edge"
              style={{
                fontSize: "10px",
                lineHeight: "1",
              }}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </foreignObject>
      )}
      {data?.label && (
        <foreignObject
          width={100}
          height={24}
          x={labelX - 50}
          y={labelY + 15}
          className="edge-label-foreignobject overflow-visible"
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div 
            className="text-xs bg-gray-800 text-white px-2 py-1 rounded border border-gray-600 text-center truncate max-w-full"
            title={data.label}
          >
            {data.label}
          </div>
        </foreignObject>
      )}
    </>
  );
};

export default RoutedEdge;
