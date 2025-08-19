import { Button } from "@/components/ui/button";
import { FaTh, FaList } from "react-icons/fa";
import { useState, useEffect, useMemo, useRef } from "react";
import { Document } from "@/types";
import { UploadTab } from "./UploadTab";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { useQuery } from "@tanstack/react-query";
import { usePaginationStore } from "@/stores/usePaginationStore";
import { DocumentFilters } from "./DocumentFilters";
import { DocumentTable } from "./DocumentsTable";
import { PageLoader } from "@/components/shared/PageLoader";
import { DocumentGrid } from "./DocumentGrid";
import { deleteDoc, fetchDocuments } from "@/api/docs";
import { useToast } from "@/hooks/use-toast";

export default function Documents() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [fileTypeFilter, setFileTypeFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const { currentPage, setPage, resetPage, itemsPerPage, } = usePaginationStore();

  const { data: documentsRaw = [], isLoading, isError, error } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
    refetchInterval: 1000,
    refetchOnMount: true, 
    refetchOnWindowFocus: true, 
  });

  // Duplicate detection toast: show when a SKIPPED duplicate is detected; dismiss when the original appears at the top
  const { toast } = useToast();
  const duplicateToastsRef = useRef<Map<string, { dismiss: () => void }>>(new Map());

  // Hide SKIPPED docs from the main list to avoid duplicates surfacing twice
  const documents = useMemo(() => {
    const visible = (documentsRaw || []).filter(d => d.status !== 'SKIPPED');
    // Sort by last_updated (desc), fall back to created_at
    const safeTime = (iso?: string) => (iso ? Date.parse(iso) : 0);
    return [...visible].sort((a, b) => {
      const at = safeTime(a.last_updated || a.created_at);
      const bt = safeTime(b.last_updated || b.created_at);
      return bt - at;
    });
  }, [documentsRaw]);

  // Manage duplicate toasts lifecycle relative to list state
  useEffect(() => {
    if (!documentsRaw?.length) return;

    const getDuplicateKey = (d: Document) => d?.type_data?.content_md5 || d?.source_name || d?.pipeline_id;

    // Show toasts for any newly detected SKIPPED duplicates
    for (const d of documentsRaw) {
      if (d?.status === 'SKIPPED') {
        const key = getDuplicateKey(d);
        if (!duplicateToastsRef.current.has(key)) {
          const t = toast({
            title: 'Duplicate document detected',
            description: `The document "${d.source_name}" has already been embedded. Making it available...`,
            variant: 'destructive',
          });
          duplicateToastsRef.current.set(key, { dismiss: t.dismiss });
        }
      }
    }

    // Dismiss any active duplicate toast when the corresponding original doc surfaces at the top
    const top = documents?.[0];
    if (top) {
      const topKey = getDuplicateKey(top);
      if (duplicateToastsRef.current.has(topKey)) {
        duplicateToastsRef.current.get(topKey)?.dismiss();
        duplicateToastsRef.current.delete(topKey);
      }
    }
  }, [documentsRaw, documents, toast]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      for (const { dismiss } of duplicateToastsRef.current.values()) {
        dismiss();
      }
      duplicateToastsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    resetPage();
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [showUploadModal, activeDoc])

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

  const viewButtons = (
    <div className="flex items-center space-x-4">
      <Button onClick={() => setShowUploadModal(true)}>Upload Document</Button>
      <div className="flex">
        <Button
          variant={viewMode === "grid" ? "default" : "outline"}
          size="icon"
          onClick={() => { setViewMode("grid"); setActiveDoc(null) }}
        >
          <FaTh />
        </Button>
        <Button
          variant={viewMode === "list" ? "default" : "outline"}
          size="icon"
          onClick={() => { setViewMode("list"); setActiveDoc(null) }}
        >
          <FaList />
        </Button>
      </div>
    </div>
  );

  const onDeleteConfirmed = async (source_id: string) => {
    try {
      setDeleteLoading(true);
      await deleteDoc(source_id);
    } catch (error) {
      console.error("Error deleting document:", error);
    } finally {
      setDeleteLoading(false);
      setActiveDoc(null);
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
                      />
                    ) : (
                      <>
                        <div className="w-full">
                          <DocumentTable
                            documents={documents}
                            activeDoc={activeDoc}
                            setActiveDoc={setActiveDoc}
                            deleteLoading={deleteLoading}
                            onDeleteConfirmed={onDeleteConfirmed}
                            retrying={retrying}
                            handleRetry={handleRetry}
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
    </div>
  );
}
