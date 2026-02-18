import React, { useMemo } from 'react';
import { EdgeProps, getSmoothStepPath } from 'reactflow';
import { X } from 'lucide-react';
import { useTheme } from "@/contexts/ThemeContext";
import { deriveThemeColors } from "@/lib/colorUtils";

interface BidirectionalOffsetEdgeProps extends EdgeProps {
  onDelete?: (edgeId: string) => void;
}

const BidirectionalOffsetEdge: React.FC<BidirectionalOffsetEdgeProps> = ({
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

  const { primaryLight: bidiColor, primaryDark: bidiColorDark } = useMemo(
    () => deriveThemeColors(primaryHex),
    [primaryHex],
  );
  // Calculate offset amount based on direction
  const offsetAmount = 15;
  const offsetDirection = data?.offsetDirection || 'right';
  const isRightOffset = offsetDirection === 'right';
  const intermediateOffset = offsetAmount * 2;
  
  // Calculate smooth step path with offset
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 15,
    // Apply offset to create curve separation
    offset: isRightOffset ? intermediateOffset : -intermediateOffset,
  });

  const handleDelete = (event: React.MouseEvent) => {
    event.stopPropagation();
    const deleteFunction = data?.onDelete || onDelete;
    if (deleteFunction) {
      deleteFunction(id);
    }
  };

  // Generate unique marker ID to avoid conflicts
  const markerId = `offset-arrow-${id}`;

  return (
    <>
      {/* Define the arrow marker - enhanced for better visibility */}
      <defs>
        <marker
          id={markerId}
          markerWidth="20"
          markerHeight="20"
          refX="18"
          refY="10"
          orient="auto"
          markerUnits="strokeWidth"
        >
          {/* Outer arrow border for contrast */}
          <path
            d="M2,2 L18,10 L2,18 L6,10 Z"
            fill="#FFFFFF"
            stroke={bidiColorDark}
            strokeWidth="1"
          />
          {/* Main arrow body */}
          <path
            d="M3,4 L16,10 L3,16 L6,10 Z"
            fill={bidiColor}
            stroke={bidiColor}
            strokeWidth="0.5"
          />
        </marker>
      </defs>

      {/* Main edge path with offset */}
      <path
        id={id}
        style={{
          ...style,
          stroke: bidiColor,
          strokeWidth: 2.5,
          fill: 'none',
          strokeLinecap: 'round',
          strokeLinejoin: 'round',
        }}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={`url(#${markerId})`}
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
            className="group opacity-0 hover:opacity-100 transition-opacity duration-200 text-white rounded-full w-5 h-5 flex items-center justify-center shadow-sm"
            style={{ backgroundColor: bidiColor, borderColor: bidiColorDark, borderWidth: 1 }}
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
          y={labelY + (isRightOffset ? 15 : -35)}
          className="edge-label-foreignobject"
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div className="text-xs text-white px-2 py-1 rounded text-center shadow-sm"
            style={{ backgroundColor: bidiColorDark, borderColor: bidiColor, borderWidth: 1 }}>
            {data.label}
          </div>
        </foreignObject>
      )}
    </>
  );
};

export default BidirectionalOffsetEdge;
