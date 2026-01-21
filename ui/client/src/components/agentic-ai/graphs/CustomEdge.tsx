
import React from 'react';
import { EdgeProps } from 'reactflow';
import { X } from 'lucide-react';

interface CustomEdgeProps extends EdgeProps {
  onDelete?: (edgeId: string) => void;
}

const CustomEdge: React.FC<CustomEdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
  onDelete,
}) => {
  const parallelOffset = Number(data?.parallelOffset ?? 0);
  const edgeOffset = 28;

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const length = Math.hypot(dx, dy) || 1;
  const normalX = -dy / length;
  const normalY = dx / length;
  const offsetX = normalX * parallelOffset * edgeOffset;
  const offsetY = normalY * parallelOffset * edgeOffset;

  const controlPoint1 = {
    x: sourceX + dx * 0.25 + offsetX,
    y: sourceY + dy * 0.25 + offsetY,
  };
  const controlPoint2 = {
    x: sourceX + dx * 0.75 + offsetX,
    y: sourceY + dy * 0.75 + offsetY,
  };

  const edgePath = `M ${sourceX},${sourceY} C ${controlPoint1.x},${controlPoint1.y} ${controlPoint2.x},${controlPoint2.y} ${targetX},${targetY}`;
  const labelX = sourceX + dx * 0.5 + offsetX;
  const labelY = sourceY + dy * 0.5 + offsetY;

  const handleDelete = (event: React.MouseEvent) => {
    event.stopPropagation();
    // Try to get onDelete from data first, then from props
    const deleteFunction = data?.onDelete || onDelete;
    if (deleteFunction) {
      deleteFunction(id);
    }
  };

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
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
            title="Delete edge"
            style={{
              fontSize: '10px',
              lineHeight: '1',
            }}
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </foreignObject>
      {/* Edge label if exists */}
      {data?.label && (
        <foreignObject
          width={60}
          height={20}
          x={labelX - 30}
          y={labelY + 15}
          className="edge-label-foreignobject"
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div className="text-xs bg-gray-800 text-white px-2 py-1 rounded border border-gray-600 text-center">
            {data.label}
          </div>
        </foreignObject>
      )}
    </>
  );
};

export default CustomEdge;
