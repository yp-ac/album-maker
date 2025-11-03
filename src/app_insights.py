"""
Application Insights integration for monitoring and telemetry.
"""
import os
import logging
from typing import Optional
from opencensus.ext.azure import metrics_exporter
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module


class AppInsights:
    """Application Insights telemetry client."""
    
    def __init__(self):
        """Initialize Application Insights if connection string is available."""
        self.connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        self.enabled = bool(self.connection_string)
        
        if self.enabled:
            self._setup_logging()
            self._setup_metrics()
        else:
            logging.info("Application Insights not configured (missing connection string)")
    
    def _setup_logging(self):
        """Configure Azure Log Handler."""
        logger = logging.getLogger(__name__)
        logger.addHandler(AzureLogHandler(connection_string=self.connection_string))
        logger.setLevel(logging.INFO)
        logging.info("Application Insights logging enabled")
    
    def _setup_metrics(self):
        """Setup custom metrics."""
        self.stats = stats_module.stats
        self.view_manager = self.stats.view_manager
        
        # Define measures
        self.images_processed = measure_module.MeasureInt(
            "images_processed",
            "Number of images processed",
            "images"
        )
        
        self.clusters_created = measure_module.MeasureInt(
            "clusters_created",
            "Number of clusters created",
            "clusters"
        )
        
        self.blur_images_filtered = measure_module.MeasureInt(
            "blur_images_filtered",
            "Number of blurry images filtered",
            "images"
        )
        
        self.duplicates_found = measure_module.MeasureInt(
            "duplicates_found",
            "Number of duplicate images found",
            "images"
        )
        
        self.processing_time = measure_module.MeasureFloat(
            "processing_time",
            "Image processing time",
            "seconds"
        )
        
        # Create views
        images_view = view_module.View(
            "images_processed_view",
            "Total images processed",
            [],
            self.images_processed,
            aggregation_module.CountAggregation()
        )
        
        clusters_view = view_module.View(
            "clusters_created_view",
            "Total clusters created",
            [],
            self.clusters_created,
            aggregation_module.LastValueAggregation()
        )
        
        # Register views
        self.view_manager.register_view(images_view)
        self.view_manager.register_view(clusters_view)
        
        # Setup exporter
        exporter = metrics_exporter.new_metrics_exporter(
            connection_string=self.connection_string
        )
        self.view_manager.register_exporter(exporter)
        
        logging.info("Application Insights metrics enabled")
    
    def track_images_processed(self, count: int):
        """Track number of images processed."""
        if self.enabled:
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            mmap.measure_int_put(self.images_processed, count)
            mmap.record(tmap)
            logging.info(f"Tracked: {count} images processed")
    
    def track_clusters_created(self, count: int):
        """Track number of clusters created."""
        if self.enabled:
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            mmap.measure_int_put(self.clusters_created, count)
            mmap.record(tmap)
            logging.info(f"Tracked: {count} clusters created")
    
    def track_blur_filtered(self, count: int):
        """Track number of blurry images filtered."""
        if self.enabled:
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            mmap.measure_int_put(self.blur_images_filtered, count)
            mmap.record(tmap)
            logging.info(f"Tracked: {count} blurry images filtered")
    
    def track_duplicates_found(self, count: int):
        """Track number of duplicates found."""
        if self.enabled:
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            mmap.measure_int_put(self.duplicates_found, count)
            mmap.record(tmap)
            logging.info(f"Tracked: {count} duplicates found")
    
    def track_processing_time(self, seconds: float):
        """Track processing time."""
        if self.enabled:
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            mmap.measure_float_put(self.processing_time, seconds)
            mmap.record(tmap)
            logging.info(f"Tracked: {seconds:.2f}s processing time")
    
    def track_event(self, event_name: str, properties: Optional[dict] = None):
        """Track custom event."""
        if self.enabled:
            props = properties or {}
            logging.info(f"Event: {event_name}", extra=props)
    
    def track_exception(self, exception: Exception):
        """Track exception."""
        if self.enabled:
            logging.exception(f"Exception occurred: {str(exception)}")


# Global instance
app_insights = AppInsights()
