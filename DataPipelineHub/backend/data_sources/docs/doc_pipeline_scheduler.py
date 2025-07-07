import logging
import datetime
from typing import Dict, List
from utils.monitor.pipeline_monitor import SourceType, PipelineStatus
from utils.monitor.pipeline_monitor import PipelineMonitor
from utils.monitor.docs.doc_pipeline_monitor import DocPipelineMonitor

class DocDataPipeline:
    """Document data pipeline that integrates with the monitoring system."""
    
    def __init__(self, mongo_client, monitor=None, doc_monitor=None, logger=None):
        """
        Initialize the Document data pipeline.
        
        Args:
            mongo_client: MongoDB client instance
            monitor: Existing PipelineMonitor instance (optional)
            doc_monitor: Existing DocPipelineMonitor instance (optional)
            logger: Existing logger instance to use (optional)
        """
        # Initialize the main pipeline monitor
        self.monitor = PipelineMonitor(mongo_client) if not monitor else monitor
        
        # Initialize the specialized Document monitor
        self.doc_monitor = DocPipelineMonitor(self.monitor) if not doc_monitor else doc_monitor
        
        # Use the provided logger or create a new one
        self.logger = logger if logger else logging.getLogger("doc_data_pipeline")
        self.logger.info("Initialized DocDataPipeline")

    def register_doc(self, doc_id: str, doc_name: str, upload_by: str, scope: str) -> bool:
        """
        Insert a document to mongo.
        
        This method registers the document pipeline and updates its status to in queue.
        
        Args:
            doc_id: The ID of the document to process
            doc_name: The name/title of the document
            upload_by: The user who uploaded the document
            
        Returns:
            Boolean indicating success or failure
        """
        pipeline_id = f"doc_{doc_id}"
        
        # Register pipeline with monitor
        self.logger.info(f"Registering document pipeline: {pipeline_id}")
        self.monitor.register_pipeline(pipeline_id, SourceType.DOCUMENT, doc_name, upload_by, scope)
        
        try:
            # Update status to active
            self.logger.info(f"Setting document pipeline {pipeline_id} to PENDING")
            self.monitor.update_pipeline_status(pipeline_id, PipelineStatus.PENDING)
            
            # Log document processing start
            self.logger.info(f"Moving to insert document: {doc_id})")
            return True
        except Exception as e:
            # Log error and update pipeline status
            error_message = f"Error registering document {doc_id}: {str(e)}"
            self.logger.error(error_message)
            self.monitor.record_error(pipeline_id, error_message)
            return False
        
    def process_doc(self, doc_id: str) -> bool:
        """
        Process a document.
        
        This method registers the document pipeline and updates its status to active.
        
        Args:
            doc_id: The ID of the document to process
            doc_name: The name/title of the document
            
        Returns:
            Boolean indicating success or failure
        """
        pipeline_id = f"doc_{doc_id}"
        
        # Register pipeline with monitor
        self.logger.info(f"Registering document pipeline: {pipeline_id}")
        
        try:
            # Update status to active
            self.logger.info(f"Setting document pipeline {pipeline_id} to ACTIVE")
            self.monitor.update_pipeline_status(pipeline_id, PipelineStatus.ACTIVE)
            
            # Log document processing start
            self.logger.info(f"Starting to process document with ID: {doc_id})")
            return True
        except Exception as e:
            # Log error and update pipeline status
            error_message = f"Error processing document {doc_id}: {str(e)}"
            self.logger.error(error_message)
            self.monitor.record_error(pipeline_id, error_message)
            return False
    
    def complete_doc_processing(self, doc_id: str, doc_name: str) -> bool:
        """
        Mark a document pipeline as done.
        
        Args:
            doc_id: The ID of the document
            doc_name: The name/title of the document
            
        Returns:
            Boolean indicating success or failure
        """
        pipeline_id = f"doc_{doc_id}"
        
        try:
            # Update status to completed
            self.logger.info(f"Setting document pipeline {pipeline_id} to DONE")
            self.monitor.update_pipeline_status(pipeline_id, PipelineStatus.DONE)
            
            # Log completion
            self.logger.info(f"Completed processing document: {doc_name} (ID: {doc_id})")
            return True
        except Exception as e:
            # Log error
            error_message = f"Error completing document pipeline for {doc_name}: {str(e)}"
            self.logger.error(error_message)
            self.monitor.record_error(pipeline_id, error_message)
            return False

    def fail_doc_processing(self, doc_id: str, doc_name: str, error_message: str) -> bool:
        """
        Mark a document pipeline as failed.
        
        Args:
            doc_id: The ID of the document
            doc_name: The name/title of the document
            error_message: Description of the error
            
        Returns:
            Boolean indicating operation success
        """
        pipeline_id = f"doc_{doc_id}"
        
        try:
            # Update status to failed
            self.logger.info(f"Setting document pipeline {pipeline_id} to FAILED")
            self.monitor.update_pipeline_status(pipeline_id, PipelineStatus.FAILED)
            
            # Record the error
            self.monitor.record_error(pipeline_id, error_message)
            
            # Log failure
            self.logger.error(f"Failed processing document: {doc_name} (ID: {doc_id}): {error_message}")
            return True
        except Exception as e:
            # Log error about the error handling (meta-error)
            meta_error = f"Error marking document pipeline as failed for {doc_name}: {str(e)}"
            self.logger.error(meta_error)
            return False

    def get_pipeline_dashboard_data(self) -> Dict:
        """
        Get comprehensive data for a monitoring dashboard.
        
        Returns:
            Dictionary containing dashboard data
        """
        self.logger.info("Generating document pipeline dashboard data")
        
        # Get overall document stats
        doc_stats = self.doc_monitor.get_all_docs_stats()
        
        # Get active document pipelines
        active_docs = self.doc_monitor.get_active_docs()
        
        # Get recent activity
        recent_activity = self.doc_monitor.get_recent_docs_activity(10)
        
        # Create dashboard data object
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "doc_stats": doc_stats,
            "active_docs": active_docs,
            "recent_activity": recent_activity
        }
        
        self.logger.debug(f"Generated dashboard data with {len(active_docs)} active docs and {len(recent_activity)} recent activities")
        return dashboard_data

    def process_doc_batch(self, docs: List[Dict[str, str]]) -> Dict[str, bool]:
        """
        Process a batch of documents.
        
        Args:
            docs: List of dictionaries containing doc_id and doc_name
            
        Returns:
            Dictionary mapping doc_ids to success/failure status
        """
        self.logger.info(f"Processing batch of {len(docs)} documents")
        results = {}
        
        for doc in docs:
            doc_id = doc.get("doc_id")
            doc_name = doc.get("doc_name", f"Unknown-{doc_id}")
            
            if not doc_id:
                self.logger.warning(f"Skipping document with missing ID: {doc}")
                continue
            
            results[doc_id] = self.process_doc(doc_id, doc_name)
        
        self.logger.info(f"Batch processing complete. Successful: {list(results.values()).count(True)}, Failed: {list(results.values()).count(False)}")
        return results