import React, { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Eye, Loader2 } from "lucide-react";
import { BuildingBlock } from "@/types/graph";
import { getCategoryDisplay } from "@/components/shared/helpers";
import ResourceDetailsModal from "./ResourceDetailsModal";
import { useTheme } from "@/contexts/ThemeContext";
import { deriveThemeColors } from "@/lib/colorUtils";

interface BuildingBlocksSidebarProps {
  buildingBlocks: BuildingBlock[];
  isLoading: boolean;
  onDragStart: (event: React.DragEvent, block: BuildingBlock) => void;
  usedElementIds?: Set<string>;
}

const BuildingBlocksSidebar: React.FC<BuildingBlocksSidebarProps> = ({
  buildingBlocks,
  isLoading,
  onDragStart,
  usedElementIds = new Set<string>(),
}) => {
  const [selectedElement, setSelectedElement] = useState<BuildingBlock | null>(
    null,
  );
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const { primaryHex } = useTheme();

  const themeColors = useMemo(() => {
    const t = deriveThemeColors(primaryHex);
    return {
      iconBg: t.primary,
    };
  }, [primaryHex]);

  const handleViewDetails = (block: BuildingBlock) => {
    setSelectedElement(block);
    setIsDetailsModalOpen(true);
  };

  const handleDragStart = (event: React.DragEvent, block: BuildingBlock) => {
    if (usedElementIds.has(block.id)) {
      event.preventDefault();
      return;
    }
    onDragStart(event, block);
  };

  return (
    <div className="w-80 h-full">
      <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col">
        <CardHeader className="py-3 px-6 border-b border-gray-800">
          <CardTitle className="text-lg font-heading">Nodes</CardTitle>
        </CardHeader>
        <CardContent className="p-4 flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 min-h-0">
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-2 text-sm text-gray-400">
                  Loading blocks...
                </span>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 350px)' }}>
                {buildingBlocks.map((block) => {
                  const isUsed = usedElementIds.has(block.id);
                  return (
                    <Card
                      key={block.id}
                      className={`transition-colors ${
                        isUsed
                          ? 'bg-gray-900 border-gray-800 opacity-50 cursor-not-allowed'
                          : 'bg-gray-800 border-gray-700 hover:border-gray-600 cursor-grab active:cursor-grabbing'
                      }`}
                      draggable={!isUsed}
                      onDragStart={(event) => handleDragStart(event, block)}
                    >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold text-white"
                               style={{ backgroundColor: themeColors.iconBg }}>
                            {getCategoryDisplay(block.workspaceData?.category || "default").icon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className={`font-medium text-sm truncate ${isUsed ? 'text-gray-500' : 'text-white'}`}>
                                {block.label}
                              </h4>
                              {isUsed && (
                                <span className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">
                                  Used
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-400 truncate">
                              {block.workspaceData?.type || block.type}
                            </p>
                          </div>
                        </div>
                        {block.workspaceData && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-gray-400 hover:text-white"
                            onClick={() => handleViewDetails(block)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* Fixed Instructions Footer */}
          {!isLoading && (
            <div className="mt-4 p-4 bg-gray-900 rounded-lg border border-gray-700 flex-shrink-0">
              <h4 className="font-medium text-white mb-2">How to use:</h4>
              <div className="text-xs text-gray-400 space-y-1">
                <p>• Drag nodes from sidebar to canvas</p>
                <p>• Connect nodes to build workflow</p>
                <p>• Always start with User Input node</p>
                <p>• End workflow with Final Answer node</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Resource Details Modal */}
      <ResourceDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
        element={selectedElement}
      />
    </div>
  );
};

export default BuildingBlocksSidebar;
