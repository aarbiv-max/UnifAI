"""DataSource domain model."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class DataSource:
    """Domain model for a data source."""
    source_id: str
    source_name: str
    source_type: str
    pipeline_id: str
    upload_by: str
    created_at: datetime
    last_sync_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    type_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataSource":
        """
        Create a DataSource instance from a mapping of field values.
        
        Parameters:
            data (Dict[str, Any]): Dictionary containing keys for DataSource fields. Recognized keys:
                - "source_id", "source_name", "source_type", "pipeline_id", "upload_by": default to "" if missing.
                - "created_at", "last_sync_at": default to the current datetime if missing.
                - "tags": defaults to an empty list if missing.
                - "type_data": defaults to an empty dict if missing.
        
        Returns:
            DataSource: A DataSource populated from the provided dictionary.
        """
        return cls(
            source_id=data.get("source_id", ""),
            source_name=data.get("source_name", ""),
            source_type=data.get("source_type", ""),
            pipeline_id=data.get("pipeline_id", ""),
            upload_by=data.get("upload_by", ""),
            created_at=data.get("created_at", datetime.now()),
            last_sync_at=data.get("last_sync_at", datetime.now()),
            tags=data.get("tags", []),
            type_data=data.get("type_data", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Produce a dictionary representation of the DataSource instance.
        
        All dataclass fields are included in the resulting mapping.
        
        Returns:
            A dictionary containing the DataSource's fields and their current values.
        """
        return asdict(self)
