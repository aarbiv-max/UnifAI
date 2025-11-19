import { Button } from "@/components/ui/button";
import { FaTh, FaList, FaTrash } from "react-icons/fa";
import { useState, useEffect } from "react";
import { Document } from "@/types";
import { UploadTab } from "./UploadTab";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePaginationStore } from "@/stores/usePaginationStore";
import { DocumentFilters } from "./DocumentFilters";
import { DocumentTable } from "./DocumentsTable";
import { PageLoader } from "@/components/shared/PageLoader";
import { DocumentGrid } from "./DocumentGrid";
import { deleteDoc, fetchDocuments } from "@/api/docs";
import { RowSelectionState } from "@tanstack/react-table";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { useToast } from "@/hooks/use-toast";

export default function Documents() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [fileTypeFilter, setFileTypeFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState<{ open: boolean; count: number }>({ open: false, count: 0 });
  const [bulkDeleteLoading, setBulkDeleteLoading] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { currentPage, setPage, resetPage, itemsPerPage, } = usePaginationStore();

  const { data: documents = [], isLoading, isError, error, refetch } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
    staleTime: 15 * 1000, // Consider data fresh for 15 seconds
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    refetchInterval: false, // Disable automatic polling - only refetch when needed
  });

  useEffect(() => {
    resetPage();
  }, []);

  // Invalidate queries when upload modal closes to refresh the list
  useEffect(() => {
    if (!showUploadModal) {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  }, [showUploadModal, queryClient]);

  // Clear selection when filters change to avoid confusion
  useEffect(() => {
    setRowSelection({});
  }, [fileTypeFilter, searchQuery]);

  const filteredDocuments = documents.filter((doc) => {
    const matchesType = fileTypeFilter === "all" || doc.type_data.file_type === fileTypeFilter;
    const matchesSearch = doc.source_name?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const totalPages = Math.ceil(filteredDocuments.length / itemsPerPage);
  const paginatedDocuments = filteredDocuments.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const startIndex = (currentPage - 1) * itemsPerPage + 1;
  const endIndex = Math.min(currentPage * itemsPerPage, filteredDocuments.length);
  const footer = (
    <div className="flex items-center justify-between w-full px-4">
      <span className="text-sm text-gray-400">
        Showing {startIndex}-{endIndex} of {filteredDocuments.length} documents
      </span>

      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(Math.max(currentPage - 1, 1))}
          disabled={currentPage === 1}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(Math.min(currentPage + 1, totalPages))}
          disabled={currentPage === totalPages}
        >
          Next
        </Button>

      </div>
    </div>
  );

  const filters = (
    <DocumentFilters
      fileTypeFilter={fileTypeFilter}
      setFileTypeFilter={setFileTypeFilter}
      searchQuery={searchQuery}
      setSearchQuery={setSearchQuery}
    />
  );

  const selectedCount = Object.keys(rowSelection).length;

  const handleDeleteSelected = () => {
    const selectedIds = Object.keys(rowSelection);
    if (selectedIds.length === 0) return;
    setBulkDeleteConfirm({ 
      open: true, 
      count: selectedIds.length
    });
  };

  const viewButtons = (
    <div className="flex items-center space-x-4">
      <Button
        variant="destructive"
        onClick={handleDeleteSelected}
        disabled={bulkDeleteLoading || deleteLoading || selectedCount === 0}
      >
        <FaTrash className="mr-2 h-3 w-3" />
        Delete {selectedCount} Selected
      </Button>
      <Button onClick={() => setShowUploadModal(true)}>Upload Document</Button>
      <div className="flex">
        <Button
          variant={viewMode === "list" ? "default" : "outline"}
          size="icon"
          onClick={() => { setViewMode("list"); setActiveDoc(null) }}
        >
          <FaList />
        </Button>
        <Button
          variant={viewMode === "grid" ? "default" : "outline"}
          size="icon"
          onClick={() => { setViewMode("grid"); setActiveDoc(null) }}
        >
          <FaTh />
        </Button>
      </div>
    </div>
  );

  const onDeleteConfirmed = async (source_id: string) => {
    try {
      setDeleteLoading(true);
      await deleteDoc(source_id);
      // Invalidate queries to refresh the list after successful deletion
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: "✅ Document Deleted",
        description: "The document has been successfully deleted.",
        variant: "default",
      });
    } catch (error) {
      console.error("Error deleting document:", error);
      toast({
        title: "❌ Deletion Failed",
        description: error instanceof Error ? error.message : "Failed to delete document.",
        variant: "destructive",
      });
      throw error; // Re-throw to let the modal handle the error state
    } finally {
      setDeleteLoading(false);
      setActiveDoc(null);
    }
  };

  const handleBulkDelete = async (ids: string[]) => {
    try {
      setBulkDeleteLoading(true);
      // Delete all selected documents in parallel
      await Promise.all(ids.map(id => deleteDoc(id)));
      
      // Clear selection and refresh
      setRowSelection({});
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      
      toast({
        title: "✅ Documents Deleted",
        description: `Successfully deleted ${ids.length} document${ids.length > 1 ? 's' : ''}.`,
        variant: "default",
      });
    } catch (error) {
      console.error("Error deleting documents:", error);
      toast({
        title: "❌ Bulk Deletion Failed",
        description: error instanceof Error ? error.message : "Failed to delete some documents.",
        variant: "destructive",
      });
      throw error;
    } finally {
      setBulkDeleteLoading(false);
      // Don't close modal here - let confirmBulkDelete handle it after success
    }
  };

  const confirmBulkDelete = async () => {
    try {
      setBulkDeleteLoading(true);
      // Delete selected documents
      const idsToDelete = Object.keys(rowSelection);
      
      await handleBulkDelete(idsToDelete);
      // Only close modal after successful deletion
      setBulkDeleteConfirm({ open: false, count: 0 });
    } catch (error) {
      // Error already handled in handleBulkDelete - keep modal open on error
      console.error("Bulk delete failed:", error);
    } finally {
      setBulkDeleteLoading(false);
    }
  };

  const handleRetry = async (id: string) => {
    try {
      setRetrying(true);
      // await axiosInstance.put("/api/docs/retry.embedding", { "pipelineId": id });
    } catch (error) {
      console.error("Error retrying embedding:", error);
    } finally {
      setRetrying(false);
    }
  };
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          title="Document Library"
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />

        <div className="flex-1 overflow-auto px-6 pb-6">
          {showUploadModal ? (
            <UploadTab setShowUploadModal={setShowUploadModal} fetchDocuments={fetchDocuments} />
          ) : (
            <div className="mt-6">
              {isLoading ? (
                <PageLoader />
              ) : isError ? (
                <p className="text-sm text-red-500">Error: {(error as Error).message}</p>
              ) : (
                <>
                  {/* Top controls: filters only in grid view, view buttons and upload always */}
                  <div className="flex items-center justify-between mb-4">
                    {viewMode === "grid" ? (<div className="flex-1">{filters}</div>) : (<div className="flex-1" />)}
                    {viewButtons}
                  </div>

                  {documents.length ? (
                    viewMode === "grid" ? (
                      <DocumentGrid
                        paginatedDocuments={paginatedDocuments}
                        activeDoc={activeDoc}
                        setActiveDoc={setActiveDoc}
                        deleteLoading={deleteLoading}
                        onDeleteConfirmed={onDeleteConfirmed}
                        retrying={retrying}
                        handleRetry={handleRetry}
                        footer={footer}
                        rowSelection={rowSelection}
                        onRowSelectionChange={setRowSelection}
                      />
                    ) : (
                      <>
                        <div className="w-full">
                          <DocumentTable
                            documents={filteredDocuments}
                            activeDoc={activeDoc}
                            setActiveDoc={setActiveDoc}
                            deleteLoading={deleteLoading}
                            onDeleteConfirmed={onDeleteConfirmed}
                            retrying={retrying}
                            handleRetry={handleRetry}
                            rowSelection={rowSelection}
                            onRowSelectionChange={setRowSelection}
                          />

                        </div>
                      </>
                    )
                  ) : (
                    <p>No documents available.</p>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bulk Delete Confirmation Dialog */}
      <ConfirmDialog
        open={bulkDeleteConfirm.open}
        title="Delete Selected Documents"
        message={`Are you sure you want to delete ${bulkDeleteConfirm.count} selected document${bulkDeleteConfirm.count > 1 ? 's' : ''}? This action cannot be undone.`}
        confirmLabel="Yes, Delete"
        cancelLabel="Cancel"
        loading={bulkDeleteLoading}
        onCancel={() => {
          if (!bulkDeleteLoading) {
            setBulkDeleteConfirm({ open: false, count: 0 });
          }
        }}
        onConfirm={confirmBulkDelete}
      />
    </div>
  );
}
