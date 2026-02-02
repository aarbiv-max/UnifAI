import React, { useState, useEffect } from 'react';
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Plus, Info } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { CategorySidebar } from '../components/agentic-ai/workspace/CategorySidebar';
import { ElementGrid } from '../components/agentic-ai/workspace/ElementGrid';
import { ElementForm } from '../components/agentic-ai/workspace/ElementForm';
import { ElementType, ElementInstance } from '../types/workspace';
import { UmamiTrack } from '@/components/ui/umamitrack';
import { UmamiEvents } from '@/config/umamiEvents';
import { SelectionCheckbox } from '@/components/shared/SelectionCheckbox';
import { BulkDeleteButton } from '@/components/shared/BulkDeleteButton';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { useSimpleBulkDelete, useSetSelection } from '@/hooks/use-bulk-delete';
import SimpleTooltip from '@/components/shared/SimpleTooltip';

export default function UserWorkspace() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedElementType, setSelectedElementType] = useState<ElementType | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingElement, setEditingElement] = useState<ElementInstance | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [elementToDelete, setElementToDelete] = useState<ElementInstance | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
    saveElement,
    deleteElement
  } = useWorkspaceData();

  // Multi-select state using the reusable hook
  const {
    selectedIds,
    handleSelectionChange,
    clearSelection,
    isAllSelected,
    selectedCount,
  } = useSetSelection<string>();

  // Bulk delete using the reusable hook
  const {
    bulkDeleteConfirm,
    bulkDeleteLoading,
    openBulkDeleteConfirm,
    closeBulkDeleteConfirm,
    executeBulkDelete,
  } = useSimpleBulkDelete({
    deleteItem: deleteElement,
    itemName: selectedElementType?.name?.toLowerCase() || 'element',
    onSuccess: () => {
      clearSelection();
      if (selectedElementType) {
        fetchElementInstances(selectedElementType.category, selectedElementType.type);
      }
    },
  });

  // Clear selection when element type changes
  useEffect(() => {
    clearSelection();
  }, [selectedElementType, clearSelection]);

  // Handle select all
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      elementInstances.forEach(el => handleSelectionChange(el.rid, true));
    } else {
      clearSelection();
    }
  };

  // Fetch element instances when element type is selected
  useEffect(() => {
    if (selectedElementType) {
      fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
  }, [selectedElementType, fetchElementInstances]);

  const handleElementTypeSelect = async (category: string, elementType: ElementType) => {
    // Ensure category is set before element type to avoid race conditions
    setSelectedCategory(category);
    setSelectedElementType(elementType);
    await Promise.all([
      fetchElementSchema(category, elementType.type),
      fetchElementActions(category, elementType.type)
    ]);
  };

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
      // Refresh instances
      fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
  };

  const handleDeleteElement = (rid: string) => {
    const element = elementInstances.find(el => el.rid === rid);
    if (element) {
      setElementToDelete(element);
      setShowDeleteModal(true);
    }
  };

  const confirmDeleteElement = async () => {
    if (!elementToDelete || !selectedElementType) return;

    setIsDeleting(true);
    try {
      await deleteElement(elementToDelete.rid);
      // Refresh instances
      await fetchElementInstances(selectedElementType.category, selectedElementType.type);
      setShowDeleteModal(false);
      setElementToDelete(null);
    } catch (error) {
      console.error('Error deleting element:', error);
      // Error handling is done in the deleteElement function via toast
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDeleteElement = () => {
    setShowDeleteModal(false);
    setElementToDelete(null);
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
                    <div className="flex items-center gap-4">
                      <div>
                        <h2 className="text-2xl font-heading font-bold">
                          {selectedElementType.name} Instances
                        </h2>
                        <p className="text-gray-400 text-sm">
                          Manage your {selectedElementType.name.toLowerCase()} configurations
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2 items-center">
                      {selectedCount > 0 && (
                        <BulkDeleteButton
                          selectedCount={selectedCount}
                          onClick={() => openBulkDeleteConfirm(selectedIds)}
                          itemName={selectedElementType?.name?.toLowerCase() || 'element'}
                        />
                      )}
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

                      {elementInstances.length > 0 && (
                        <SimpleTooltip content={<p>{isAllSelected(elementInstances.map(el => el.rid)) ? 'Unselect all' : 'Select all'}</p>}>
                          <div className="flex items-center justify-center w-9 h-9 rounded-md border border-gray-700 hover:bg-background-dark">
                            <SelectionCheckbox
                              checked={isAllSelected(elementInstances.map(el => el.rid))}
                              onCheckedChange={handleSelectAll}
                              ariaLabel={isAllSelected(elementInstances.map(el => el.rid)) ? 'Unselect all elements' : 'Select all elements'}
                            />
                          </div>
                        </SimpleTooltip>
                      )}

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

                {/* Elements Grid */}
                <div className="flex-1">
                  {selectedElementType ? (
                    <ElementGrid
                      elements={elementInstances}
                      elementType={selectedElementType}
                      isLoading={isLoadingInstances}
                      onEditElement={handleEditElement}
                      onDeleteElement={handleDeleteElement}
                      elementSchema={elementSchema}
                      selectedIds={selectedIds}
                      onSelectionChange={handleSelectionChange}
                      selectionEnabled={true}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center text-gray-400">
                        <p className="text-lg font-medium mb-2">Select an element type</p>
                        <p className="text-sm">Choose a category and element type from the sidebar to view instances</p>
                      </div>
                    </div>
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

      {/* Bulk Delete Confirmation Dialog */}
      <ConfirmDialog
        open={bulkDeleteConfirm.open}
        title={`Delete ${bulkDeleteConfirm.count} ${selectedElementType?.name || 'Element'}(s)`}
        message={`Are you sure you want to delete ${bulkDeleteConfirm.count} selected ${selectedElementType?.name?.toLowerCase() || 'element'}(s)? This action cannot be undone.`}
        confirmLabel="Yes, Delete"
        cancelLabel="Cancel"
        loading={bulkDeleteLoading}
        onCancel={closeBulkDeleteConfirm}
        onConfirm={executeBulkDelete}
      />
    </div>
  );
}