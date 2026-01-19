"""Monitoring application service - log processing and metrics tracking."""
from datetime import datetime
import logging
from collections import deque
from typing import Dict, List, Optional, Any

from domain.monitoring.model import MetricsEntry, ErrorEntry, LogEntry
from domain.monitoring.repository import MonitoringRepository
from domain.pipeline.repository import PipelineRepository

from application.common.parsing import LogParser, SlackLogParser, DocLogParser


class MonitoringService:
    """
    Application service for pipeline monitoring.
    
    Handles log processing, metrics tracking, and provides monitoring
    capabilities through the MonitoringRepository port.
    """
    
    def __init__(
        self,
        monitoring_repo: MonitoringRepository,
        pipeline_repo: PipelineRepository,
    ):
        """
        Create a MonitoringService that coordinates monitoring and pipeline repositories, logging, and an in-memory cache for recent logs.
        
        Parameters:
            monitoring_repo (MonitoringRepository): Repository used to persist metrics, errors, and logs.
            pipeline_repo (PipelineRepository): Repository used to access and update pipeline records.
        """
        self._monitoring_repo = monitoring_repo
        self._pipeline_repo = pipeline_repo
        self._logger = logging.getLogger(__name__)
        
        # In-memory cache of recent logs for quick access
        self._recent_logs_cache: Dict[str, deque] = {}
        
        # Handler reference for cleanup
        self._monitoring_handler: Optional[logging.Handler] = None
        self._monitoring_logger: Optional[logging.Logger] = None

    def log_metrics(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """
        Persist and register metrics for a pipeline.
        
        Updates the pipeline's aggregated statistics and saves a metrics snapshot associated with the pipeline's source type. If the pipeline cannot be found, the method returns without modifying state.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to which the metrics belong.
            metrics (Dict[str, Any]): Mapping of metric names to their values to be recorded.
        """
        pipeline = self._pipeline_repo.find_by_id(pipeline_id)
        if not pipeline:
            self._logger.warning(f"Attempted to log metrics for non-existent pipeline: {pipeline_id}")
            return
        
        print(f"Logging metrics for pipeline {pipeline_id}: {metrics}")
        
        # Increment pipeline stats
        self._pipeline_repo.increment_stats(pipeline_id, metrics)
        
        # Save metrics snapshot
        entry = MetricsEntry(
            pipeline_id=pipeline_id,
            source_type=pipeline.source_type,
            metrics=metrics,
        )
        self._monitoring_repo.save_metrics(entry)
        self._logger.info(f"Logged metrics for pipeline {pipeline_id}: {metrics}")

    def record_error(
        self,
        pipeline_id: str,
        error_message: str,
        error_details: Optional[Dict] = None,
    ) -> None:
        """
        Record an error for the specified pipeline and persist it to the monitoring repository.
        
        If the pipeline ID is not found, logs a warning and returns without saving.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline associated with the error.
            error_message (str): Human-readable description of the error.
            error_details (Optional[Dict]): Additional structured details about the error; defaults to an empty dict when not provided.
        """
        pipeline = self._pipeline_repo.find_by_id(pipeline_id)
        if not pipeline:
            self._logger.warning(f"Attempted to record error for non-existent pipeline: {pipeline_id}")
            return
        
        entry = ErrorEntry(
            pipeline_id=pipeline_id,
            source_type=pipeline.source_type,
            error_message=error_message,
            error_details=error_details or {},
        )
        self._monitoring_repo.save_error(entry)
        self._logger.error(f"Error in pipeline {pipeline_id}: {error_message}")

    def get_source_stats(self, source_type: str) -> Dict:
        """
        Retrieve aggregated statistics for the given source type.
        
        Parameters:
            source_type (str): Identifier of the source type (e.g., "SLACK", "DOCUMENT").
        
        Returns:
            dict: Aggregated statistics keyed by metric names (for example, "api_calls", "documents_retrieved", counts or other numeric metrics).
        """
        return self._pipeline_repo.get_source_stats(source_type)

    def get_recent_activity(self, source_type: str, limit: int = 10) -> List[str]:
        """
        Retrieve up to `limit` recent log messages for the given source type.
        
        Parameters:
            source_type (str): Source type to filter logs by.
            limit (int): Maximum number of messages to return.
        
        Returns:
            List[str]: List of log message strings (up to `limit` most recent).
        """
        logs = self._monitoring_repo.get_logs_by_source(source_type, limit)
        return [log.message for log in logs]

    def process_log_line(self, log_line: str, pipeline_id: Optional[str] = None) -> None:
        """
        Parse a single log line, persist a structured log entry, update the in-memory recent-log cache, and record any metrics extracted for the associated pipeline.
        
        Parameters:
            log_line (str): Raw log line to be parsed and processed.
            pipeline_id (Optional[str]): Optional pipeline identifier to associate with the log and metrics; if omitted, the method will attempt to extract a pipeline ID from the log line.
        """
        timestamp, module, level, message = LogParser.parse_log_line(log_line)
        
        # Determine source type from log content
        source_type = self._detect_source_type(message, pipeline_id, module)
        
        # Extract pipeline ID if not provided
        if not pipeline_id:
            pipeline_id = self._extract_pipeline_id(log_line, source_type)
        
        # Update recent logs cache
        if source_type not in self._recent_logs_cache:
            self._recent_logs_cache[source_type] = deque(maxlen=10)
        self._recent_logs_cache[source_type].appendleft(log_line)
        
        # Store log entry
        log_entry = LogEntry(
            source_type=source_type,
            message=message,
            level=level,
            module=module,
            timestamp=timestamp,
            pipeline_id=pipeline_id,
        )
        self._monitoring_repo.save_log(log_entry)
        
        # Extract and update metrics
        metrics = self._extract_metrics(log_line, source_type)
        if metrics and pipeline_id:
            self.log_metrics(pipeline_id, metrics)

    def _detect_source_type(self, message: str, pipeline_id: Optional[str], module: str) -> str:
        """
        Infer the log's source type as "SLACK", "DOCUMENT", or "OTHER" based on message content, pipeline id, and module name.
        
        Parameters:
            message (str): The log message text to inspect.
            pipeline_id (Optional[str]): Pipeline identifier; used to detect Slack-related pipelines when it contains "slack".
            module (str): The originating module name; used to detect document-related modules when it starts with "docling".
        
        Returns:
            str: "`SLACK` if the message contains 'Slack' or the pipeline_id contains 'slack', `DOCUMENT` if the message mentions document types (e.g., 'document', 'pdf', 'docx') or the module starts with 'docling', `OTHER` otherwise."
        """
        if "Slack" in message or (pipeline_id and 'slack' in pipeline_id):
            return "SLACK"
        elif "document" in message.lower() or "pdf" in message.lower() or "docx" in message.lower() or module.startswith("docling"):
            return "DOCUMENT"
        return "OTHER"

    def _extract_pipeline_id(self, log_line: str, source_type: str) -> Optional[str]:
        """
        Derive a pipeline identifier from a log line for the given source type.
        
        Parameters:
            log_line (str): Raw log text to inspect for an identifier.
            source_type (str): Source category used to select extraction logic; expected values include `"SLACK"` and `"DOCUMENT"`.
        
        Returns:
            pipeline_id (Optional[str]): `'slack_<channel_id>'` for Slack logs or `'doc_<doc_id>'` for Document logs when an identifier is found, `None` otherwise.
        """
        if source_type == "SLACK":
            channel_id = SlackLogParser.extract_slack_channel_id(log_line)
            if channel_id:
                return f"slack_{channel_id}"
        elif source_type == "DOCUMENT":
            doc_id = DocLogParser.extract_doc_id(log_line)
            if doc_id:
                return f"doc_{doc_id}"
        return None

    def _extract_metrics(self, log_line: str, source_type: str) -> Dict[str, Any]:
        """
        Derive monitoring metrics from a single log line for the specified source type.
        
        Parses the log line using source-specific and generic extractors and returns a dictionary of observed metric counters. Possible keys include:
        - `api_calls`: number of API calls observed (1 when an API endpoint is detected).
        - `documents_retrieved`: number of documents retrieved or started for processing.
        - `chunks_generated`: number of chunks produced.
        - `embeddings_created`: number of embeddings created.
        
        Parameters:
            source_type (str): Source category of the log ("SLACK", "DOCUMENT", or other) which controls source-specific extraction rules.
        
        Returns:
            Dict[str, Any]: Mapping of metric names to their extracted values; empty if no metrics were found.
        """
        metrics: Dict[str, Any] = {}
        
        # Process based on source type
        if source_type == "SLACK":
            # Count API calls
            api_endpoint = SlackLogParser.extract_api_endpoint(log_line)
            if api_endpoint:
                metrics["api_calls"] = 1
            
            # Track message counts
            message_count = SlackLogParser.extract_message_count(log_line)
            if message_count:
                metrics["documents_retrieved"] = message_count
        
        elif source_type == "DOCUMENT":
            # For document pipelines, each pipeline represents one document
            if "Processing document" in log_line or "Started processing" in log_line:
                metrics["documents_retrieved"] = 1
            
            # Count API calls for document processing
            api_endpoint = DocLogParser.extract_api_endpoint(log_line)
            if api_endpoint:
                metrics["api_calls"] = 1
            
            # Track chunk counts (document-specific patterns)
            chunk_count = DocLogParser.extract_chunk_count(log_line)
            if chunk_count:
                metrics["chunks_generated"] = chunk_count
            
            # Track embedding counts (document-specific patterns)
            embedding_count = DocLogParser.extract_embedding_count(log_line)
            if embedding_count:
                metrics["embeddings_created"] = embedding_count
        
        # Generic patterns (base LogParser)
        chunk_count = LogParser.extract_chunk_count(log_line)
        if chunk_count and "chunks_generated" not in metrics:
            metrics["chunks_generated"] = chunk_count
        
        embedding_count = LogParser.extract_embedding_count(log_line)
        if embedding_count and "embeddings_created" not in metrics:
            metrics["embeddings_created"] = embedding_count
        
        return metrics

    def start_log_monitoring(self, pipeline_id: str = "", target_logger: Optional[logging.Logger] = None) -> None:
        """
        Attach a handler to a logger that forwards formatted log records into the service's log-processing pipeline, optionally associating them with a specific pipeline ID.
        
        Parameters:
            pipeline_id (str): Optional pipeline identifier to associate with every captured log message. If empty, captured logs are processed without an explicit pipeline association.
            target_logger (logging.Logger | None): Logger to monitor. If omitted, the service's internal logger is used.
        """
        if target_logger is None:
            target_logger = self._logger
        
        self._logger.info(f"Starting log monitoring for logger: {target_logger.name}")
        
        service = self
        
        class MonitoringHandler(logging.Handler):
            def __init__(self):
                """
                Initialize a MonitoringService instance.
                
                Performs base-class initialization.
                """
                super().__init__()
            
            def emit(self, record: logging.LogRecord) -> None:
                """
                Handle a logging record by formatting it and sending the resulting log line to the monitoring service tied to the handler's pipeline.
                
                Parameters:
                    record (logging.LogRecord): The log record to format and process.
                """
                log_line = self.format(record)
                service.process_log_line(log_line, pipeline_id)
        
        handler = MonitoringHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        target_logger.addHandler(handler)
        
        self._monitoring_handler = handler
        self._monitoring_logger = target_logger

    def finish_log_monitoring(self) -> None:
        """
        Stop and detach the active monitoring log handler.
        
        If a monitoring handler is attached, removes it from its logger and clears internal references; does nothing if no handler is active.
        """
        if self._monitoring_handler and self._monitoring_logger:
            self._monitoring_logger.removeHandler(self._monitoring_handler)
            self._monitoring_handler = None
            self._monitoring_logger = None
            self._logger.info("Finished log monitoring")
