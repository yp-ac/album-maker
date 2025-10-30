from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Image:
    """Represents an image in the album maker system."""
    id: Optional[int] = None
    filename: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None
    blur_score: float = 0.0
    hash: str = ""
    cluster_id: Optional[int] = None
    is_duplicate: bool = False
    duplicate_group: Optional[int] = None

@dataclass
class Cluster:
    """Represents a cluster of images grouped by location and time."""
    id: Optional[int] = None
    name: str = ""
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    image_count: int = 0

@dataclass
class DuplicateGroup:
    """Represents a group of duplicate images with a best image selected."""
    id: Optional[int] = None
    best_image_id: Optional[int] = None
    image_ids: str = ""  # JSON string array of image IDs