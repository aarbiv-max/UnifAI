import logging
import datetime
from utils.monitor.pipeline_monitor import SourceType, PipelineStatus
from utils.monitor.pipeline_monitor import PipelineMonitor
from utils.monitor.slack.slack_pipeline_monitor import SlackPipelineMonitor

class SlackDataPipeline:
    """Slack data pipeline that integrates with the monitoring system."""
    
    def __init__(self, mongo_client, monitor=None, slack_monitor=None, logger=None):
        """
        Initialize the Slack data pipeline.
        
        Args:
            mongo_client: MongoDB client instance
            logger: Existing logger instance to use (default: None, will use shared logger)
        """
        # Initialize the main pipeline monitor
        self.monitor = PipelineMonitor(mongo_client) if not monitor else monitor
        
        # Initialize the specialized Slack monitor
        self.slack_monitor = SlackPipelineMonitor(self.monitor) if not slack_monitor else slack_monitor
        
        # Use the provided logger or the shared logger instead of creating a new one
        self.logger = logger if logger else logging.getLogger("data_pipeline")

    def process_slack_channel(self, channel_id, channel_name):
        """
        Process a Slack channel.
        
        This example method demonstrates how to integrate the pipeline monitoring
        into your existing data processing code.
        
        Args:
            channel_id: The ID of the Slack channel to process
            channel_name: The name of the Slack channel
        """
        pipeline_id = f"slack_{channel_id}"
        
        # Register pipeline with monitor
        self.monitor.register_pipeline(pipeline_id, SourceType.SLACK)
        
        try:
            # Update status to active
            self.monitor.update_pipeline_status(pipeline_id, PipelineStatus.ACTIVE)
            
            # Log channel processing start
            self.logger.info(f"Starting to process Slack channel: {channel_name} (ID: {channel_id})")
            return pipeline_id
        except Exception as e:
            # Log error and update pipeline status
            error_message = f"Error processing Slack channel {channel_name}: {str(e)}"
            self.logger.error(error_message)
            self.monitor.record_error(pipeline_id, error_message)
            return None

    def get_pipeline_dashboard_data(self):
        """
        Get data for a monitoring dashboard.
        
        Returns:
            Dictionary containing dashboard data
        """
        # Get overall Slack stats
        slack_stats = self.slack_monitor.get_all_slack_stats()
        
        # Get active pipelines
        active_pipelines = self.slack_monitor.get_active_channels()
        
        # Get recent activity
        recent_activity = self.slack_monitor.get_recent_slack_activity(10)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "slack_stats": slack_stats,
            "active_pipelines": active_pipelines,
            "recent_activity": recent_activity
        }