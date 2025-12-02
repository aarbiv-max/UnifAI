import React, { useMemo } from 'react';
import { EdgeProps, getSmoothStepPath } from 'reactflow';
import { X } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { getPaletteColor } from '@/lib/colorUtils';

interface BidirectionalEdgeProps extends EdgeProps {
  onDelete?: (edgeId: string) => void;
}

const BidirectionalEdge: React.FC<BidirectionalEdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  data,
  onDelete,
}) => {
  const { primaryHex } = useTheme();
  
  // Calculate smooth step path
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 15,
  });

  const handleDelete = (event: React.MouseEvent) => {
    event.stopPropagation();
    const deleteFunction = data?.onDelete || onDelete;
    if (deleteFunction) {
      // If this is a bidirectional edge, delete both original edges
      if (data?.originalEdgeIds && Array.isArray(data.originalEdgeIds) && data.originalEdgeIds.length === 2) {
        // Delete both original edges - need to delete both directions
        const [edge1Id, edge2Id] = data.originalEdgeIds;
        // Delete first edge
        deleteFunction(edge1Id);
        // Delete second edge (use setTimeout to ensure first deletion completes)
        setTimeout(() => {
          deleteFunction(edge2Id);
        }, 0);
      } else {
        // Fallback to deleting the bidirectional edge ID
        deleteFunction(id);
      }
    }
  };

  // Generate unique marker IDs - use edge ID which should be unique
  // Sanitize the ID to ensure it's valid for SVG marker IDs
  const sanitizedId = id.replace(/[^a-zA-Z0-9-]/g, '_');
  const markerStartId = `bidir-start-${sanitizedId}`;
  const markerEndId = `bidir-end-${sanitizedId}`;

  // Get color from primary palette - use index 1 for bidirectional edges (slightly different from regular)
  // Use useMemo to recalculate when primaryHex changes
  const edgeColor = useMemo(() => getPaletteColor(primaryHex, 1, 6), [primaryHex]);

  // Default style for bidirectional edges - thicker and using primary color palette
  // Merge with incoming style but ensure stroke uses our palette color
  const defaultStyle: React.CSSProperties = useMemo(() => ({
    stroke: edgeColor,
    strokeWidth: 4, // Thicker than regular edges (which are typically 2-3)
    fill: 'none',
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    ...style, // Merge with incoming style
    stroke: edgeColor, // Override stroke to always use palette color
  }), [edgeColor, style]);

  return (
    <>
      {/* Define arrow markers for both ends - larger for better visibility */}
      <defs>
        {/* Start marker (arrow pointing backwards towards source) */}
        <marker
          id={markerStartId}
          markerWidth="18"
          markerHeight="18"
          refX="15"
          refY="9"
          orient="auto-start-reverse"
          markerUnits="userSpaceOnUse"
        >
          {/* Arrow shape - larger */}
          <path
            d="M1,3 L15,9 L1,15 L5,9 Z"
            fill={edgeColor}
            stroke={edgeColor}
            strokeWidth="0.4"
            opacity="0.9"
          />
        </marker>
        
        {/* End marker (arrow pointing forwards towards target) */}
        <marker
          id={markerEndId}
          markerWidth="18"
          markerHeight="18"
          refX="15"
          refY="9"
          orient="auto"
          markerUnits="userSpaceOnUse"
        >
          {/* Arrow pointing forwards - larger */}
          <path
            d="M1,3 L15,9 L1,15 L5,9 Z"
            fill={edgeColor}
            stroke={edgeColor}
            strokeWidth="0.4"
            opacity="0.9"
          />
        </marker>
      </defs>

      {/* Main edge path with arrows on both ends */}
      <path
        id={id}
        style={defaultStyle}
        className="react-flow__edge-path"
        d={edgePath}
        markerStart={`url(#${markerStartId})`}
        markerEnd={`url(#${markerEndId})`}
      />

      {/* Delete button positioned at the middle of the edge */}
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
            className="group opacity-0 hover:opacity-100 transition-opacity duration-200 bg-red-600 hover:bg-red-700 text-white rounded-full w-5 h-5 flex items-center justify-center border border-red-500 shadow-sm"
            onClick={handleDelete}
            title={`Delete edge ${id}`}
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </foreignObject>

      {/* Edge label if exists */}
      {data?.label && (
        <foreignObject
          width={80}
          height={20}
          x={labelX - 40}
          y={labelY + 15}
          className="edge-label-foreignobject"
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div className="text-xs bg-gray-800 text-white px-2 py-1 rounded border border-gray-600 text-center shadow-sm">
            {data.label}
          </div>
        </foreignObject>
      )}
    </>
  );
};

export default BidirectionalEdge;
