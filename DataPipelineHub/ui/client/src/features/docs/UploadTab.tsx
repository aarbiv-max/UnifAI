import { useState, useEffect } from "react";
import type React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FaFileAlt, FaUpload, FaTimes } from "react-icons/fa";
import { Progress } from "@/components/ui/progress";
import { CircleX } from "lucide-react";
import { ProcessingOptions } from "./ProcessingOptions";
import { embedDocs, uploadDocs, getSupportedFileExtensions } from "@/api/docs";
import { useAuth } from '@/contexts/AuthContext';
import { toast } from "@/hooks/use-toast";
import { validateFiles, formatFileSizeErrors, formatExtensionErrors, MAX_FILE_SIZE_MB } from "@/utils/fileValidation";
import { formatPipelineError } from "@/utils/errorFormatting";

interface UploadTabProps {
    setShowUploadModal: (showUploadModal: boolean) => void;
    fetchDocuments: () => Promise<any>;
}

export const UploadTab: React.FC<UploadTabProps> = ({
    setShowUploadModal, fetchDocuments
}) => {
    const { user } = useAuth();
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string>("");
    const [supportedExtensions, setSupportedExtensions] = useState<string[]>([]);
    
    useEffect(() => {
        const loadSupportedExtensions = async () => {
            try {
                const extensions = await getSupportedFileExtensions();
                setSupportedExtensions(extensions);
            } catch (err) {
                console.error("Failed to load supported extensions:", err);
                setSupportedExtensions([".pdf", ".docx", ".txt"]);
            }
        };
        loadSupportedExtensions();
    }, []);
    
    const isFileExtensionSupported = (fileName: string): boolean => {
        const extension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
        return supportedExtensions.includes(extension);
    };
    
    const handleDragEnter = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
    };

    const handleFiles = (files: FileList) => {
        const { validFiles, invalidFiles, sizeErrors } = validateFiles(files, isFileExtensionSupported);
        
        const errorMessages: string[] = [];
        
        if (invalidFiles.length > 0) {
            errorMessages.push(formatExtensionErrors(invalidFiles));
        }
        
        if (sizeErrors.length > 0) {
            errorMessages.push(formatFileSizeErrors(sizeErrors));
        }
        
        if (errorMessages.length > 0) {
            setError(errorMessages.join('\n'));
        } else {
            setError(""); // Clear any previous errors if no invalid files
        }
        
        if (validFiles.length > 0) {
            const currentFileCount = selectedFiles.length;
            const totalAfterAdd = currentFileCount + validFiles.length;
            
            if (totalAfterAdd > 5) {
                const remainingSlots = 5 - currentFileCount;
                if (remainingSlots <= 0) {
                    setError("Maximum of 5 documents allowed. Please remove some files before adding new ones.");
                } else {
                    setError(`Maximum of 5 documents allowed. You can add ${remainingSlots} more document${remainingSlots === 1 ? '' : 's'}.`);
                }
                return;
            }
            
            setSelectedFiles((prev) => [...prev, ...validFiles]);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        handleFiles(e.target.files ? e.target.files : new FileList());
    };

    const uploadFiles = async (files: File[]) => {
        setIsUploading(true);
        setUploadProgress(0);
        let uploadedCount = 0;

        try {
            for (const file of files) {
                const base64 = await new Promise<string>((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const result = reader.result as string;
                        resolve(result.split(",")[1]);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
                
                await uploadDocs([{ name: file.name, content: base64 }])

                uploadedCount += 1;
                setUploadProgress(uploadedCount);
            }

            setIsUploading(false);
            // Refetch documents immediately after upload to show new documents
            await fetchDocuments();
            setShowUploadModal(false);
        } catch (err) {
            console.error("Upload failed", err);
            const message = (err as Error)?.message || "Upload failed. Please try again.";
            setError(message);
            toast({
                variant: "destructive",
                title: (
                    <span className="inline-flex items-center gap-2">
                        <CircleX className="h-4 w-4 text-red-500" />
                        <span>Upload failed</span>
                    </span>
                ),
                description: message,
            });
            setIsUploading(false);
            throw err; // Propagate to caller so downstream steps (embed) are not started
        }
    };

    const startPipeline = async (docs: {source_name: string}[]) => {
        try {
            const res = await embedDocs(docs, user?.username || 'default');
            const issues = res?.registration?.issues || [];

            if (issues.length > 0) {
                // Backend provides: { doc_name, issue_type, message }
                issues.forEach((issue: any) => {
                    const { title: titleText, description } = formatPipelineError(issue);
                    
                    const title: React.ReactNode = (
                        <span className="inline-flex items-center gap-2">
                            <CircleX className="h-4 w-4 text-red-500" />
                            <span>{titleText}</span>
                        </span>
                    );

                    toast({
                        variant: "destructive",
                        title,
                        description,
                    });
                });
            }
        } catch (error) {
            console.error(error);
            const message = (error as Error)?.message || "Failed to start embedding pipeline.";
            setError(message);
            toast({
                variant: "destructive",
                title: (
                    <span className="inline-flex items-center gap-2">
                        <CircleX className="h-4 w-4 text-red-500" />
                        <span>Embedding failed</span>
                    </span>
                ),
                description: message,
            });
        }
    }

    const handleSubmit = async () => {
        if (selectedFiles.length === 0) return;
        try {
            await uploadFiles(selectedFiles);
        } catch {
            // Upload error already toasted; do not proceed to embedding
            return;
        }
        const docs = selectedFiles.map((file) => ({source_name: file.name}));
        await startPipeline(docs);
        // Refetch documents immediately after pipeline starts to show new documents
        await fetchDocuments();
        setSelectedFiles([]);
    };


    return (
        <div className="space-y-6">
            <Card className="bg-background-card shadow-card border-gray-800 w-full">
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center">
                            <FaFileAlt className="text-accent text-2xl mr-3" />
                            <div>
                                <h3 className="text-lg font-heading font-semibold">
                                    Upload Documents
                                </h3>
                            </div>
                        </div>
                        <Button variant="outline" onClick={() => setShowUploadModal(false)}>
                            Cancel
                        </Button>
                    </div>

                    <div
                        className={`border-2 border-dashed rounded-lg transition-colors ${
                            selectedFiles.length >= 5 
                                ? "border-gray-500 cursor-not-allowed opacity-50" 
                                : isDragging 
                                    ? "border-primary bg-primary bg-opacity-5 cursor-pointer" 
                                    : "border-gray-700 hover:border-gray-600 cursor-pointer"
                        }`}
                        onDragEnter={selectedFiles.length < 5 ? handleDragEnter : undefined}
                        onDragLeave={selectedFiles.length < 5 ? handleDragLeave : undefined}
                        onDragOver={selectedFiles.length < 5 ? handleDragOver : undefined}
                        onDrop={selectedFiles.length < 5 ? handleDrop : undefined}
                        onClick={selectedFiles.length < 5 ? () => document.getElementById("file-upload")?.click() : undefined}
                    >
                        {!isUploading ? (
                            <div className="p-8">
                                <div className="flex flex-col items-center justify-center text-center">
                                    <div className="w-16 h-16 bg-background-surface rounded-full flex items-center justify-center mb-4">
                                        <FaUpload className="text-accent text-xl" />
                                    </div>
                                    <p className="font-semibold text-base mb-1">
                                        {selectedFiles.length >= 5 ? "Maximum files reached" : "Drag and drop files here"}
                                    </p>
                                    <p className="text-sm text-gray-400 mb-4">
                                        {selectedFiles.length >= 5 ? "Remove files to add more" : "or click to browse files"}
                                    </p>
                                    <div className="flex flex-col items-center gap-2 text-xs text-gray-500">
                                        <p>
                                            Supported formats: {supportedExtensions.map(ext => ext.toUpperCase().substring(1)).join(', ')}
                                        </p>
                                        <p>
                                            Maximum file size: <span className="font-semibold text-gray-400">50 MB</span> per file
                                        </p>
                                        <p>
                                            Maximum files: <span className="font-semibold text-gray-400">5</span> documents
                                        </p>
                                    </div>
                                </div>
                                <input id="file-upload" type="file" multiple className="hidden" onChange={handleFileSelect}/>
                            </div>
                        ) : (
                            <div className="p-8">
                                <div className="flex items-center justify-between mb-4">
                                    <span className="font-semibold text-base">
                                        Uploading files...
                                    </span>
                                    <Button variant="ghost" size="sm" onClick={() => setIsUploading(false)}>
                                        <FaTimes className="h-4 w-4" />
                                    </Button>
                                </div>
                                <Progress value={(uploadProgress / selectedFiles.length) * 100} className="h-2 mb-3" />
                                <div className="text-sm text-gray-300 text-center">
                                    {uploadProgress === selectedFiles.length
                                        ? "Upload complete!"
                                        : `Uploading ${uploadProgress} of ${selectedFiles.length} files...`}
                                </div>
                            </div>
                        )}

                        {/* File list after upload */}
                        {selectedFiles.length > 0 && !isUploading && (
                            <div className="border-t border-gray-700 pt-4 px-4 pb-4">
                                <div className="flex justify-between items-center mb-3">
                                    <span className="text-sm font-medium text-gray-300">
                                        Selected Files ({selectedFiles.length} of 5)
                                    </span>
                                </div>
                                <ul className="space-y-2">
                                    {selectedFiles.map((file, idx) => {
                                        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
                                        return (
                                            <li key={idx} className="flex items-center justify-between text-gray-300 bg-background-surface px-3 py-2.5 rounded-md border border-gray-700">
                                                <div className="flex-1 min-w-0 mr-3">
                                                    <span className="block truncate text-sm font-medium">{file.name}</span>
                                                    <span className="block text-xs text-gray-500 mt-0.5">{fileSizeMB} MB</span>
                                                </div>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation(); 
                                                        setSelectedFiles((prev) =>
                                                            prev.filter((_, i) => i !== idx)
                                                        );
                                                    }}
                                                    className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors p-1"
                                                    title="Remove file"
                                                >
                                                    <FaTimes className="w-4 h-4" />
                                                </button>
                                            </li>
                                        );
                                    })}
                                </ul>
                            </div>
                        )}
                        {error && (
                            <div className="px-4 pb-4">
                                <p className="text-sm text-red-500 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2 whitespace-pre-line">{error}</p>
                            </div>
                        )}
                    </div>
                </CardContent>
                {selectedFiles.length > 0 && !isUploading && (
                    <div className="flex justify-end items-center gap-3 px-6 py-4 border-t border-gray-700 bg-background-surface/50">
                        <span className="text-sm text-gray-400">
                            {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} ready to upload
                        </span>
                        <Button disabled={selectedFiles.length === 0} onClick={handleSubmit}>
                            Upload {selectedFiles.length} Document{selectedFiles.length > 1 ? 's' : ''}
                        </Button>
                    </div>
                )}
            </Card>

            <ProcessingOptions />
        </div>
    )
}

