import React from "react";
import { getPaletteColor } from "@/lib/colorUtils";

type EdgeLegendProps = {
  primaryColor: string;
  bidirectionalColor?: string;
  className?: string;
  markerIdPrefix?: string;
};

export default function EdgeLegend({
  primaryColor,
  bidirectionalColor,
  className = "",
  markerIdPrefix = "edge-legend",
}: EdgeLegendProps): React.ReactElement {
  const bidirectionalStroke =
    bidirectionalColor || getPaletteColor(primaryColor, 1, 4);

  const arrowId = `${markerIdPrefix}-arrow`;
  const bidirArrowId = `${markerIdPrefix}-arrow-bidir`;

  return (
    <div
      className={`min-w-[150px] rounded-lg border border-gray-700 bg-black/70 px-3 py-2 text-xs text-gray-200 backdrop-blur ${className}`}
    >
      <div className="mb-2 font-medium text-gray-100">Edge Legend</div>

      {/* Unidirectional */}
      <div className="flex items-center gap-2">
        <svg width="38" height="12" viewBox="0 0 38 12">
          <defs>
            <marker
              id={arrowId}
              markerWidth="4"
              markerHeight="4"
              refX="3.5"
              refY="2"
              orient="auto"
            >
              <path d="M0,0 L4,2 L0,4 Z" fill={primaryColor} />
            </marker>
          </defs>
          <line
            x1="2"
            y1="6"
            x2="34"
            y2="6"
            stroke={primaryColor}
            strokeWidth="1.75"
            markerEnd={`url(#${arrowId})`}
          />
        </svg>
        <span>Unidirectional</span>
      </div>

      {/* Bidirectional */}
      <div className="mt-2 flex items-center gap-2">
        <svg width="38" height="12" viewBox="0 0 38 12">
          <defs>
            <marker
              id={bidirArrowId}
              markerWidth="5"
              markerHeight="5"
              refX="4"
              refY="2.5"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L5,2.5 L0,5 Z" fill={bidirectionalStroke} />
            </marker>
          </defs>
          <line
            x1="2"
            y1="6"
            x2="34"
            y2="6"
            stroke={bidirectionalStroke}
            strokeWidth="2.25"
            markerStart={`url(#${bidirArrowId})`}
            markerEnd={`url(#${bidirArrowId})`}
          />
        </svg>
        <span>Bidirectional</span>
      </div>
    </div>
  );
}
