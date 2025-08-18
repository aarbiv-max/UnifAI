import React, { useState, useEffect } from 'react';
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from 'lucide-react';
import { CategorySidebar } from '../components/agentic-ai/workspace/CategorySidebar';
import { ElementGrid } from '../components/agentic-ai/workspace/ElementGrid';
import { ElementForm } from '../components/agentic-ai/workspace/ElementForm';
import { useWorkspaceData } from '../hooks/useWorkspaceData';
import { ElementCategory, ElementType, ElementInstance } from '../types/workspace';

export default function UserWorkspace() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedElementType, setSelectedElementType] = useState<ElementType | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingElement, setEditingElement] = useState<ElementInstance | null>(null);

  const {
    categories,
    elementInstances,
    elementSchema,
    elementActions,
    isLoading,
    fetchElementInstances,
    fetchElementSchema,
    fetchElementActions,
    saveElement,
    deleteElement
  } = useWorkspaceData();

  // Fetch element instances when element type is selected
  useEffect(() => {
    if (selectedElementType) {
      fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
  }, [selectedElementType, fetchElementInstances]);

  const handleElementTypeSelect = async (category: string, elementType: ElementType) => {
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

  const handleDeleteElement = async (rid: string) => {
    if (selectedElementType) {
      await deleteElement(rid);
      // Refresh instances
      fetchElementInstances(selectedElementType.category, selectedElementType.type);
    }
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
                    <Button 
                      onClick={handleCreateNew}
                      className="bg-primary hover:bg-opacity-80"
                      disabled={!elementSchema}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Create New
                    </Button>
                  </div>
                )}

                {/* Elements Grid */}
                <div className="flex-1">
                  {selectedElementType ? (
                    <ElementGrid
                      elements={elementInstances}
                      elementType={selectedElementType}
                      isLoading={isLoading}
                      onEditElement={handleEditElement}
                      onDeleteElement={handleDeleteElement}
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
    </div>
  );
}