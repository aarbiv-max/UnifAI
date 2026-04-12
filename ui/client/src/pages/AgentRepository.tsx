import React, { useState, useEffect } from 'react';
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Plus, Info, Search, X } from 'lucide-react';
import { FaProjectDiagram } from "react-icons/fa";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { CategorySidebar } from '../components/agentic-ai/workspace/CategorySidebar';
import { ElementGrid } from '../components/agentic-ai/workspace/ElementGrid';
import { ElementForm } from '../components/agentic-ai/workspace/ElementForm';
import { ElementData } from '../components/agentic-ai/workspace/ElementData';
import { ResourceInUseModal, InUseData } from '../components/agentic-ai/workspace/ResourceInUseModal';
import { ElementType, ElementInstance } from '../types/workspace';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import GraphDisplay from "@/components/agentic-ai/graphs/GraphDisplay";
import { fetchResolvedBlueprint, WorkflowBlueprint } from "@/api/blueprints";
import { useAuth } from "@/contexts/AuthContext";
import { UmamiTrack } from '@/components/ui/umamitrack';
import { UmamiEvents } from '@/config/umamiEvents';
import { useToast } from "@/hooks/use-toast";

export default function UserWorkspace() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedElementType, setSelectedElementType] = useState<ElementType | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingElement, setEditingElement] = useState<ElementInstance | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [elementToDelete, setElementToDelete] = useState<ElementInstance | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const [showInUseModal, setShowInUseModal] = useState(false);
  const [inUseData, setInUseData] = useState<InUseData | null>(null);
  const [replacementOptions, setReplacementOptions] = useState<Array<{ rid: string; name: string; type: string }>>([]);
  const [isLoadingReplacements, setIsLoadingReplacements] = useState(false);

  const [previewWorkflow, setPreviewWorkflow] = useState<WorkflowBlueprint | null>(null);
  const [isWorkflowPreviewOpen, setIsWorkflowPreviewOpen] = useState(false);

  const [previewResource, setPreviewResource] = useState<ElementInstance | null>(null);
  const [previewResourceType, setPreviewResourceType] = useState<ElementType | null>(null);
  const [isResourcePreviewOpen, setIsResourcePreviewOpen] = useState(false);

  const { user } = useAuth();
  const { toast } = useToast();

  const {
    categories,
    elementInstances,
    elementSchema,
    elementActions,
    isLoading,
    isLoadingInstances,
    fetchElementInstances,
    fetchElementSchema,
    fetchElementActions,
    fetchResourcesForCategory,
    fetchResourceById,
    checkElementUsage,
    saveElement,
    deleteElement,
    forceDeleteElement,
  } = useWorkspaceData();

  useEffect(() => {
    if (selectedElementType) {
      fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
  }, [selectedElementType, fetchElementInstances]);

  const handleElementTypeSelect = async (category: string, elementType: ElementType) => {
    setSelectedCategory(category);
    setSelectedElementType(elementType);
    setSearchQuery("");
    await Promise.all([
      fetchElementSchema(category, elementType.type),
      fetchElementActions(category, elementType.type)
    ]);
  };

  const filteredInstances = searchQuery.trim()
    ? elementInstances.filter(el =>
        el.name?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : elementInstances;

  const handleCreateNew = () => {
    setEditingElement(null);
    setIsFormOpen(true);
  };

  const handleEditElement = (element: ElementInstance) => {
    setEditingElement(element);
    setIsFormOpen(true);
  };

  const handleSaveElement = async (elementData: any) => {
    if (selectedElementType) {
      await saveElement(selectedElementType.category, selectedElementType.type, elementData, editingElement?.rid);
      setIsFormOpen(false);
      fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
  };

  const handleDeleteElement = async (rid: string) => {
    const element = elementInstances.find(el => el.rid === rid);
    if (!element) return;

    setElementToDelete(element);

    try {
      const usage = await checkElementUsage(rid);
      if ('inUse' in usage && usage.inUse) {
        setInUseData({
          category: usage.category,
          allowed_mode: usage.allowed_mode as "replace" | "detach" | "cascade",
          blueprints: usage.blueprints,
          resources: usage.resources,
        });
        setShowInUseModal(true);

        if (usage.allowed_mode === "replace") {
          setIsLoadingReplacements(true);
          try {
            const options = await fetchResourcesForCategory(usage.category);
            setReplacementOptions(
              options.filter((o: { rid: string }) => o.rid !== element.rid)
            );
          } finally {
            setIsLoadingReplacements(false);
          }
        }
      } else {
        setShowDeleteModal(true);
      }
    } catch (error) {
      console.error("Error during element deletion check:", error);
      toast({
        title: "Error",
        description: "Failed to check element usage. Please try again.",
        variant: "destructive",
      });
      setElementToDelete(null);
    }
  };

  const confirmDeleteElement = async () => {
    if (!elementToDelete || !selectedElementType) return;

    setIsDeleting(true);
    try {
      const result = await deleteElement(elementToDelete.rid);
      if (result.deleted) {
        await fetchElementInstances(selectedElementType.category, selectedElementType.type);
      }
    } catch (error) {
      console.error('Error deleting element:', error);
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
      setElementToDelete(null);
    }
  };

  const cancelDeleteElement = () => {
    setShowDeleteModal(false);
    setElementToDelete(null);
  };

  const handleForceDelete = async (
    mode: "replace" | "detach" | "cascade",
    replacementId?: string,
  ) => {
    if (!elementToDelete || !selectedElementType) return;
    const success = await forceDeleteElement(elementToDelete.rid, mode, replacementId);
    if (success) {
      setShowInUseModal(false);
      setInUseData(null);
      setElementToDelete(null);
      setReplacementOptions([]);
      await fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
  };

  const closeInUseModal = () => {
    setShowInUseModal(false);
    setInUseData(null);
    setElementToDelete(null);
    setReplacementOptions([]);
  };

  const handleBlueprintClick = async (blueprintId: string) => {
    try {
      const bp = await fetchResolvedBlueprint(blueprintId, user?.username);
      if (!bp) {
        toast({
          title: "Not Found",
          description: "Blueprint not found",
          variant: "destructive",
        });
        return;
      }
      setPreviewWorkflow(bp);
      setIsWorkflowPreviewOpen(true);
    } catch (err) {
      console.error("Error loading blueprint preview:", err);
      toast({
        title: "Error",
        description: "Failed to load blueprint preview",
        variant: "destructive",
      });
    }
  };

  const handleDependentResourceClick = async (resourceId: string, resourceCategory?: string, resourceType?: string) => {
    const resource = await fetchResourceById(resourceId);
    if (!resource) return;

    const matchedCategory = categories.find(c => c.category === (resourceCategory || resource.category));
    const elType: ElementType = matchedCategory?.elements.find(e => e.type === (resourceType || resource.type))
      || { type: resource.type, name: resource.type, category: resource.category };

    setPreviewResource({
      rid: resource.rid,
      name: resource.name,
      config: resource.cfg_dict,
      category: resource.category,
      type: resource.type,
      version: resource.version,
      created: resource.created,
      updated: resource.updated,
      nested_refs: resource.nested_refs,
    });
    setPreviewResourceType(elType);
    setIsResourcePreviewOpen(true);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title="User Workspace" onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main className="flex-1 overflow-y-auto p-6 bg-background-dark">
          <div className="grid grid-cols-12 gap-6 h-full">
            {/* Categories Sidebar */}
            <div className="col-span-12 md:col-span-3 lg:col-span-2">
              <CategorySidebar
                categories={categories}
                selectedCategory={selectedCategory}
                selectedElementType={selectedElementType}
                onElementTypeSelect={handleElementTypeSelect}
                isLoading={isLoading}
              />
            </div>

            {/* Main Content Area */}
            <div className="col-span-12 md:col-span-9 lg:col-span-10">
              <div className="flex flex-col h-full">
                {/* Header with Create Button */}
                {selectedElementType && (
                  <div className="flex justify-between items-center mb-6">
                    <div>
                      <h2 className="text-2xl font-heading font-bold">
                        {selectedElementType.name} Instances
                      </h2>
                      <p className="text-gray-400 text-sm">
                        Manage your {selectedElementType.name.toLowerCase()} configurations
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => {
                          const guidesUrl = `/guides?section=agentic-inventory`;
                          window.open(guidesUrl, '_blank');
                        }}
                        className="border-gray-700 hover:bg-background-dark"
                        title="View guides"
                      >
                        <Info className="h-4 w-4" />
                      </Button>

                      <UmamiTrack 
                        event={UmamiEvents.AGENT_REPOSITORY_CREATE_NEW_BUTTON}
                        eventData={{ elementType: selectedElementType?.name }}
                      >
                        <Button 
                          onClick={handleCreateNew}
                          className="bg-primary hover:bg-opacity-80"
                          disabled={!elementSchema}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Create New
                        </Button>
                      </UmamiTrack>
                    </div>
                  </div>
                )}

                {selectedElementType && elementInstances.length > 0 && (
                  <div className="relative mb-4">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={`Search ${selectedElementType.name.toLowerCase()}s by name...`}
                      className="w-full pl-9 pr-9 py-2 text-sm bg-background-card border border-gray-800 rounded-md text-gray-200 placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
                    />
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery("")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                )}

                {/* Elements Grid */}
                <div className="flex-1">
                  {!selectedElementType ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center text-gray-400">
                        <p className="text-lg font-medium mb-2">Select an element type</p>
                        <p className="text-sm">Choose a category and element type from the sidebar to view instances</p>
                      </div>
                    </div>
                  ) : searchQuery && filteredInstances.length === 0 && !isLoadingInstances ? (
                    <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                      <Search className="h-12 w-12 mb-4 opacity-50" />
                      <h3 className="text-lg font-medium mb-2">No matches found</h3>
                      <p className="text-sm">
                        No {selectedElementType.name.toLowerCase()}s matching "{searchQuery}"
                      </p>
                    </div>
                  ) : (
                    <ElementGrid
                      elements={filteredInstances}
                      elementType={selectedElementType}
                      isLoading={isLoadingInstances}
                      onEditElement={handleEditElement}
                      onDeleteElement={handleDeleteElement}
                      elementSchema={elementSchema}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Element Form Modal */}
          {isFormOpen && selectedElementType && elementSchema && (
            <ElementForm
              isOpen={isFormOpen}
              onClose={() => setIsFormOpen(false)}
              elementType={selectedElementType}
              elementSchema={elementSchema}
              elementActions={elementActions}
              editingElement={editingElement}
              onSave={handleSaveElement}
            />
          )}
        </main>
      </div>

      <AlertDialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <AlertDialogContent className="bg-background-card border-gray-800">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {selectedElementType?.name || 'Element'}</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{elementToDelete?.name || `${selectedElementType?.name || 'Element'} Instance`}"?
              <br /><br />
              <strong>Be aware that this action is irreversible.</strong>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={cancelDeleteElement}
              className="bg-background-dark border-gray-700 hover:bg-background-surface"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteElement}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {inUseData && (
        <ResourceInUseModal
          open={showInUseModal}
          onClose={closeInUseModal}
          elementName={elementToDelete?.name || "Element"}
          inUseData={inUseData}
          replacementOptions={replacementOptions}
          isLoadingReplacements={isLoadingReplacements}
          onForceDelete={handleForceDelete}
          onBlueprintClick={handleBlueprintClick}
          onResourceClick={handleDependentResourceClick}
        />
      )}

      <Dialog open={isWorkflowPreviewOpen} onOpenChange={(open) => {
        if (!open) {
          setIsWorkflowPreviewOpen(false);
          setPreviewWorkflow(null);
        }
      }}>
        <DialogContent className="bg-background-card border-gray-800 max-w-6xl w-[90vw] h-[85vh] flex flex-col p-0 overflow-hidden">
          <DialogHeader className="px-6 py-4 border-b border-gray-800 flex-shrink-0">
            <DialogTitle className="text-xl flex items-center gap-2">
              <FaProjectDiagram className="text-primary" />
              {previewWorkflow?.spec_dict?.name || "Workflow View"}
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-hidden p-6 min-h-0">
            {previewWorkflow && (
              <div className="h-full w-full">
                <GraphDisplay
                  blueprintId={previewWorkflow.blueprint_id}
                  specDict={previewWorkflow.spec_dict}
                  height="100%"
                  showBackground={true}
                  interactive={true}
                  centerInView={true}
                  animated={true}
                />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {previewResourceType && (
        <ElementData
          element={previewResource}
          elementType={previewResourceType}
          isOpen={isResourcePreviewOpen}
          onOpenChange={(open) => {
            setIsResourcePreviewOpen(open);
            if (!open) {
              setPreviewResource(null);
              setPreviewResourceType(null);
            }
          }}
          elementSchema={null}
        />
      )}
    </div>
  );
}
