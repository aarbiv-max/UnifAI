from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union

class DataProcessor(ABC):
    """
    Abstract base class for all data processors in the pipeline.
    
    This class defines the common interface and shared functionality
    for processing different data sources (Jira, Slack, Documents).
    """
    
    def __init__(self):
        """
        Create a DataProcessor and initialize internal storage for raw and processed items.
        
        Initializes two internal lists:
            _data: stores raw input items.
            _processed_data: stores processed output items.
        """
        self._data = []
        self._processed_data = []
        
    @property
    def data_length(self) -> int:
        """
        Number of raw data items stored in the processor.
        
        Returns:
            int: The number of raw data items.
        """
        return len(self._data)
    
    @property
    def processed_data_length(self) -> int:
        """
        Number of processed data items.
        
        Returns:
            int: The number of items in the processor's internal processed-data list.
        """
        return len(self._processed_data)
    
    @abstractmethod
    def process(self, data: Union[List[Dict[str, Any]], Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Process raw data items from the source and return them as a list of processed records.
        
        Parameters:
            data (Union[List[Dict[str, Any]], Dict[str, Any]]): A single raw item or a list of raw data items to process.
            **kwargs: Processor-specific options.
        
        Returns:
            List[Dict[str, Any]]: A list of processed data items.
        """
        pass
    
    @abstractmethod
    def clean_content(self, content: str) -> str:
        """
        Clean and normalize textual content for downstream processing.
        
        Parameters:
            content (str): Raw input text to be cleaned.
        
        Returns:
            str: Cleaned and normalized text.
        """
        pass
    
    def get_processed_data(self) -> List[Dict[str, Any]]:
        """
        Return the processor's stored processed data items.
        
        Returns:
            List[Dict[str, Any]]: The list of processed data items maintained by the processor.
        """
        return self._processed_data
