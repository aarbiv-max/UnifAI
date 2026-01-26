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
      className={`rounded-lg border border-gray-700 bg-black/70 px-3 py-2 text-xs text-gray-200 backdrop-blur ${className}`}
    >
      <div className="mb-2 font-medium text-gray-100">Edge Legend</div>
      <div className="flex items-center gap-2">
        <svg width="40" height="12" viewBox="0 0 40 12">
          <defs>
            <marker
              id={arrowId}
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L6,3 L0,6 Z" fill={primaryColor} />
            </marker>
            <marker
              id={bidirArrowId}
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L6,3 L0,6 Z" fill={bidirectionalStroke} />
            </marker>
          </defs>
          <line
            x1="2"
            y1="6"
            x2="36"
            y2="6"
            stroke={primaryColor}
            strokeWidth="2"
            markerEnd={`url(#${arrowId})`}
          />
        </svg>
        <span>Unidirectional</span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <svg width="40" height="12" viewBox="0 0 40 12">
          <line
            x1="2"
            y1="6"
            x2="36"
            y2="6"
            stroke={bidirectionalStroke}
            strokeWidth="3"
            markerEnd={`url(#${bidirArrowId})`}
          />
        </svg>
        <span>Bidirectional</span>
      </div>
    </div>
  );
}
