import React, { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Eye, Loader2 } from "lucide-react";
import { BuildingBlock } from "@/types/graph";
import { getCategoryDisplay } from "@/components/shared/helpers";
import ResourceDetailsModal from "./ResourceDetailsModal";
import { UmamiTrack } from "@/components/ui/umamitrack";
import { UmamiEvents } from "@/config/umamiEvents";
import { useTheme } from "@/contexts/ThemeContext";
import { deriveThemeColors } from "@/lib/colorUtils";

interface BuildingBlocksSidebarProps {
  buildingBlocks: BuildingBlock[];
  orchestrators: BuildingBlock[];
  conditions: BuildingBlock[];
  isLoading: boolean;
  onDragStart: (event: React.DragEvent, block: BuildingBlock) => void;
  onDragEnd?: () => void;
  usedElementIds?: Set<string>;
}

const BuildingBlocksSidebar: React.FC<BuildingBlocksSidebarProps> = ({
  buildingBlocks,
  orchestrators,
  conditions,
  isLoading,
  onDragStart,
  onDragEnd,
  usedElementIds = new Set<string>(),
}) => {
  const [selectedElement, setSelectedElement] = useState<BuildingBlock | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const { primaryHex } = useTheme();

  const themeColors = useMemo(() => {
    const t = deriveThemeColors(primaryHex);
    return {
      iconBg: t.primary,
      conditionBg: t.conditionAccent,
      conditionCardBg: t.conditionCardBg,
      conditionCardBorder: t.conditionCardBorder,
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

  const renderBlockList = (
    blocks: BuildingBlock[],
    category: "nodes" | "orchestrators" | "conditions",
  ) => {
    const iconBg =
      category === "conditions"
        ? themeColors.conditionBg
        : category === "orchestrators"
          ? "#00BFA5"
          : themeColors.iconBg;
    const cardBg =
      category === "conditions" ? themeColors.conditionCardBg : undefined;
    const cardBorder =
      category === "conditions" ? themeColors.conditionCardBorder : undefined;

    return (
      <div
        className="space-y-2 overflow-y-auto"
        style={{ maxHeight: "calc(100vh - 460px)" }}
      >
        {blocks.map((block) => {
          const isUsed = usedElementIds.has(block.id);
          return (
            <Card
              key={block.id}
              className={`transition-colors ${
                isUsed
                  ? "bg-gray-900 border-gray-800 opacity-50 cursor-not-allowed"
                  : category === "conditions"
                    ? "cursor-grab active:cursor-grabbing"
                    : "bg-gray-800 border-gray-700 hover:border-gray-600 cursor-grab active:cursor-grabbing"
              }`}
              style={
                category === "conditions" && !isUsed
                  ? { backgroundColor: cardBg, borderColor: cardBorder }
                  : undefined
              }
              draggable={!isUsed}
              onDragStart={(event) => handleDragStart(event, block)}
              onDragEnd={onDragEnd}
            >
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-1">
                    <div
                      className="flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold text-white"
                      style={{ backgroundColor: iconBg }}
                    >
                      {getCategoryDisplay(
                        category === "orchestrators" ? "orchestrators" : block.workspaceData?.category || "default",
                      ).icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4
                          className={`font-medium text-sm truncate ${isUsed ? "text-gray-500" : "text-white"}`}
                        >
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
        {blocks.length === 0 && !isLoading && (
          <p className="text-sm text-gray-500 text-center py-4">
            No items in this category
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="w-80 h-full">
      <Card className="bg-background-card shadow-card border-gray-800 h-full flex flex-col">
        <CardHeader className="py-3 px-6 border-b border-gray-800">
          <CardTitle className="text-lg font-heading">Elements</CardTitle>
        </CardHeader>
        <CardContent className="p-4 flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 min-h-0">
            <Tabs defaultValue="nodes" className="h-full flex flex-col">
              <TabsList className="grid w-full grid-cols-3 bg-gray-800">
                <TabsTrigger
                  value="nodes"
                  className="text-gray-300 data-[state=active]:text-white text-xs"
                >
                  Nodes ({buildingBlocks.length})
                </TabsTrigger>

                <TabsTrigger
                  value="orchestrators"
                  className="text-gray-300 data-[state=active]:text-white text-xs"
                >
                  Orchestrators ({orchestrators.length})
                </TabsTrigger>

                <UmamiTrack
                  event={UmamiEvents.AGENT_GRAPHS_CONDITIONS_BUTTON}
                  includeUserData={false}
                >
                  <TabsTrigger
                    value="conditions"
                    className="text-gray-300 data-[state=active]:text-white text-xs"
                  >
                    Conditions ({conditions.length})
                  </TabsTrigger>
                </UmamiTrack>
              </TabsList>

              <TabsContent value="nodes" className="mt-4">
                {isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-2 text-sm text-gray-400">
                      Loading blocks...
                    </span>
                  </div>
                ) : (
                  renderBlockList(buildingBlocks, "nodes")
                )}
              </TabsContent>

              <TabsContent value="orchestrators" className="mt-4">
                {isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-2 text-sm text-gray-400">
                      Loading orchestrators...
                    </span>
                  </div>
                ) : (
                  renderBlockList(orchestrators, "orchestrators")
                )}
              </TabsContent>

              <TabsContent value="conditions" className="mt-4">
                {isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <span className="ml-2 text-sm text-gray-400">
                      Loading conditions...
                    </span>
                  </div>
                ) : (
                  renderBlockList(conditions, "conditions")
                )}
              </TabsContent>
            </Tabs>
          </div>

          {/* Instructions Footer */}
          {!isLoading && (
            <div className="mt-4 p-4 bg-gray-900 rounded-lg border border-gray-700 flex-shrink-0">
              <h4 className="font-medium text-white mb-2">How to use:</h4>
              <div className="text-xs text-gray-400 space-y-1">
                <p>&bull; Drag nodes from sidebar to canvas</p>
                <p>&bull; Click a node, then click another to connect</p>
                <p>&bull; Choose unidirectional or bidirectional edge</p>
                <p>&bull; Drag conditions onto nodes for branching</p>
                <p>&bull; Each node supports only one condition</p>
                <p>&bull; Press Esc to cancel a pending connection</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <ResourceDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
        element={selectedElement}
      />
    </div>
  );
};

export default BuildingBlocksSidebar;
