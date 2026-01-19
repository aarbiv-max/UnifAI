"""Slack thread retriever worker - concurrent thread fetching for SlackConnector."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from infrastructure.connector.slack_thread_retriever import SlackThreadRetriever
from shared.logger import logger


class ThreadRetrieverWorker:
    """
    Worker class for concurrent retrieval of Slack thread replies.
    
    Uses a thread pool to fetch multiple threads in parallel,
    improving performance when processing channels with many threads.
    """
    
    def __init__(
        self,
        retriever: SlackThreadRetriever,
        max_workers: int = 10,
        thread_number: int = 1,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ):
        """
        Create a worker that manages a thread pool for fetching Slack thread replies concurrently.
        
        Initializes the worker with the given SlackThreadRetriever, creates a ThreadPoolExecutor, and sets the starting thread identifier and optional oldest/latest timestamp filters.
        
        Parameters:
            retriever (SlackThreadRetriever): API client used to fetch thread replies.
            max_workers (int): Maximum number of concurrent worker threads.
            thread_number (int): Starting index used to identify/log submitted thread retrieval tasks.
            oldest (Optional[str]): Optional oldest timestamp filter to apply to retrievals.
            latest (Optional[str]): Optional latest timestamp filter to apply to retrievals.
        """
        self.retriever = retriever
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = []
        self.thread_number = thread_number
        self.oldest = oldest
        self.latest = latest

    def submit(self, channel_id: str, thread_ts: str):
        """
        Schedule retrieval of replies for a Slack thread and record the scheduled task.
        
        This schedules a background task to fetch replies for the thread identified by the given channel ID and parent message timestamp, appends the created future to the worker's internal list, and increments the worker's thread identifier.
        
        Parameters:
            channel_id (str): ID of the channel containing the thread.
            thread_ts (str): Timestamp of the parent message for the thread.
        """
        future = self.executor.submit(
            self.retriever.get_thread_replies,
            channel_id,
            thread_ts,
            self.thread_number,
            self.oldest,
            self.latest,
        )
        self.thread_number = self.thread_number + 1
        self.futures.append(future)

    def gather_results(self) -> List[List[Dict[str, Any]]]:
        """
        Collect completed thread-reply results from submitted retrieval tasks.
        
        Waits for all submitted futures to finish, appends non-empty reply lists to the result, logs exceptions raised by individual tasks, and shuts down the executor.
        
        Returns:
            List[List[Dict[str, Any]]]: A list where each element is a list of message dictionaries representing replies from a single Slack thread.
        """
        results = []
        for future in as_completed(self.futures):
            try:
                replies = future.result()
                if replies:
                    results.append(replies)
            except Exception as e:
                logger.exception(f"Exception while retrieving thread replies: {e}")
        self.executor.shutdown(wait=True)
        return results
