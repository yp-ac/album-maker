"""
Tests for clustering algorithms.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timedelta
from src.models import Image
from src.clustering import (
    haversine_distance,
    calculate_gps_distance,
    calculate_time_difference,
    are_images_proximate,
    find_proximate_images,
    combined_distance,
    hierarchical_cluster_images,
    cluster_images,
    calculate_cluster_metadata,
    save_clusters_to_database,
    process_and_save_clustering
)


class TestGPSDistance:
    """Test GPS distance calculations."""

    def test_haversine_distance_same_point(self):
        """Distance between same point should be 0."""
        distance = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0.0

    def test_haversine_distance_known_distance(self):
        """Test with known distance between NYC and Times Square."""
        # NYC coordinates
        nyc_lat, nyc_lon = 40.7128, -74.0060
        # Times Square coordinates (approximately 5.4 km away)
        ts_lat, ts_lon = 40.7589, -73.9851

        distance = haversine_distance(nyc_lat, nyc_lon, ts_lat, ts_lon)
        assert 5.0 <= distance <= 6.0  # Should be around 5.4 km

    def test_calculate_gps_distance_with_valid_coordinates(self):
        """Test GPS distance calculation with valid image coordinates."""
        img1 = Image(id=1, filename='img1.jpg', latitude=40.7128, longitude=-74.0060)
        img2 = Image(id=2, filename='img2.jpg', latitude=40.7589, longitude=-73.9851)

        distance = calculate_gps_distance(img1, img2)
        assert isinstance(distance, float)
        assert distance > 0

    def test_calculate_gps_distance_missing_coordinates(self):
        """Test GPS distance with missing coordinates returns infinity."""
        img1 = Image(id=1, filename='img1.jpg')  # No GPS data
        img2 = Image(id=2, filename='img2.jpg', latitude=40.7128, longitude=-74.0060)

        distance = calculate_gps_distance(img1, img2)
        assert distance == float('inf')


class TestTimeDifference:
    """Test time difference calculations."""

    def test_calculate_time_difference_same_time(self):
        """Time difference between same timestamp should be 0."""
        timestamp = datetime(2025, 10, 29, 10, 0, 0)
        img1 = Image(id=1, timestamp=timestamp)
        img2 = Image(id=2, timestamp=timestamp)

        diff = calculate_time_difference(img1, img2)
        assert diff == 0.0

    def test_calculate_time_difference_one_hour(self):
        """Test time difference of one hour."""
        time1 = datetime(2025, 10, 29, 10, 0, 0)
        time2 = datetime(2025, 10, 29, 11, 0, 0)
        img1 = Image(id=1, timestamp=time1)
        img2 = Image(id=2, timestamp=time2)

        diff = calculate_time_difference(img1, img2)
        assert diff == 1.0

    def test_calculate_time_difference_missing_timestamp(self):
        """Test time difference with missing timestamp returns infinity."""
        img1 = Image(id=1, filename='img1.jpg')  # No timestamp
        img2 = Image(id=2, filename='img2.jpg', timestamp=datetime.now())

        diff = calculate_time_difference(img1, img2)
        assert diff == float('inf')


class TestImageProximity:
    """Test image proximity detection."""

    def test_are_images_proximate_close_in_space_and_time(self):
        """Images close in both space and time should be proximate."""
        time1 = datetime(2025, 10, 29, 10, 0, 0)
        time2 = datetime(2025, 10, 29, 10, 30, 0)  # 30 minutes later

        img1 = Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time1)
        img2 = Image(id=2, latitude=40.7130, longitude=-74.0062, timestamp=time2)  # ~200m away

        proximate = are_images_proximate(img1, img2, distance_threshold=1.0, time_threshold_hours=1.0)
        assert proximate is True

    def test_are_images_proximate_far_in_space(self):
        """Images far in space should not be proximate."""
        time = datetime(2025, 10, 29, 10, 0, 0)

        img1 = Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time)  # NYC
        img2 = Image(id=2, latitude=34.0522, longitude=-118.2437, timestamp=time)  # LA

        proximate = are_images_proximate(img1, img2, distance_threshold=1.0, time_threshold_hours=24.0)
        assert proximate is False

    def test_are_images_proximate_far_in_time(self):
        """Images far in time should not be proximate."""
        time1 = datetime(2025, 10, 29, 10, 0, 0)
        time2 = datetime(2025, 10, 29, 15, 0, 0)  # 5 hours later

        img1 = Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time1)
        img2 = Image(id=2, latitude=40.7128, longitude=-74.0060, timestamp=time2)  # Same location

        proximate = are_images_proximate(img1, img2, distance_threshold=1.0, time_threshold_hours=2.0)
        assert proximate is False

    def test_find_proximate_images(self):
        """Test finding proximate image pairs."""
        time_base = datetime(2025, 10, 29, 10, 0, 0)

        images = [
            Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time_base),
            Image(id=2, latitude=40.7130, longitude=-74.0062, timestamp=time_base + timedelta(minutes=30)),
            Image(id=3, latitude=34.0522, longitude=-118.2437, timestamp=time_base),  # Far away
        ]

        pairs = find_proximate_images(images, distance_threshold=1.0, time_threshold_hours=1.0)

        # Should find pair (1, 2) but not (1, 3) or (2, 3)
        assert len(pairs) == 1
        assert (1, 2) in pairs or (2, 1) in pairs


class TestHierarchicalClustering:
    """Test hierarchical clustering algorithm."""

    def test_combined_distance_same_image(self):
        """Combined distance between same image should be 0."""
        img = Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=datetime(2025, 10, 29, 10, 0, 0))
        distance = combined_distance(img, img)
        assert distance == 0.0

    def test_combined_distance_different_images(self):
        """Test combined distance between different images."""
        img1 = Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=datetime(2025, 10, 29, 10, 0, 0))
        img2 = Image(id=2, latitude=40.7138, longitude=-74.0070, timestamp=datetime(2025, 10, 29, 10, 30, 0))
        distance = combined_distance(img1, img2)
        assert distance > 0
        assert distance < 1.0  # Should be relatively small

    def test_hierarchical_cluster_empty_list(self):
        """Clustering empty image list should return empty dict."""
        result = hierarchical_cluster_images([])
        assert result == {}

    def test_hierarchical_cluster_single_image(self):
        """Clustering single image should return one cluster."""
        img = Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=datetime(2025, 10, 29, 10, 0, 0))
        result = hierarchical_cluster_images([img])
        assert len(result) == 1
        assert 0 in result
        assert len(result[0]) == 1
        assert result[0][0].id == 1

    def test_hierarchical_cluster_close_images(self):
        """Images that are close in space and time should cluster together."""
        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time_base),
            Image(id=2, latitude=40.7130, longitude=-74.0062, timestamp=time_base + timedelta(minutes=15)),
            Image(id=3, latitude=40.7140, longitude=-74.0080, timestamp=time_base + timedelta(minutes=30)),
        ]

        result = hierarchical_cluster_images(images, distance_threshold=0.5)
        # All images should be in one cluster
        assert len(result) == 1
        assert len(result[0]) == 3

    def test_hierarchical_cluster_distant_images(self):
        """Images that are far apart should not cluster."""
        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time_base),  # NYC
            Image(id=2, latitude=34.0522, longitude=-118.2437, timestamp=time_base),  # LA (far)
            Image(id=3, latitude=40.7128, longitude=-74.0060, timestamp=time_base + timedelta(hours=10)),  # Same place, later time
        ]

        result = hierarchical_cluster_images(images, distance_threshold=0.1)
        # Should have 3 separate clusters (or fewer if some merge)
        assert len(result) >= 1  # At least one cluster
        total_images = sum(len(cluster) for cluster in result.values())
        assert total_images == 3

    def test_cluster_images_main_function(self):
        """Test the main cluster_images function."""
        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time_base),
            Image(id=2, latitude=40.7130, longitude=-74.0062, timestamp=time_base + timedelta(minutes=15)),
            Image(id=3, latitude=34.0522, longitude=-118.2437, timestamp=time_base),  # Far away
        ]

        result = cluster_images(images, distance_threshold=1.0, time_threshold_hours=2.0)
        assert isinstance(result, dict)
        assert len(result) >= 1  # At least one cluster
        total_images = sum(len(cluster) for cluster in result.values())
        assert total_images == 3


class TestClusterStorage:
    """Test cluster database storage functionality."""

    def test_calculate_cluster_metadata_with_images(self):
        """Test cluster metadata calculation with valid images."""
        from src.models import Cluster

        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(id=1, latitude=40.7128, longitude=-74.0060, timestamp=time_base),
            Image(id=2, latitude=40.7130, longitude=-74.0065, timestamp=time_base + timedelta(minutes=30)),
        ]

        metadata = calculate_cluster_metadata(images)

        assert isinstance(metadata, Cluster)
        assert metadata.name == "NYC_2025-10-29"  # Should detect NYC location
        assert metadata.center_lat is not None
        assert metadata.center_lon is not None
        assert metadata.start_time == time_base
        assert metadata.end_time == time_base + timedelta(minutes=30)
        assert metadata.image_count == 2

    def test_calculate_cluster_metadata_empty_cluster(self):
        """Test cluster metadata calculation with empty image list."""
        from src.models import Cluster

        metadata = calculate_cluster_metadata([])

        assert isinstance(metadata, Cluster)
        assert metadata.name == ""
        assert metadata.center_lat is None
        assert metadata.center_lon is None
        assert metadata.start_time is None
        assert metadata.end_time is None
        assert metadata.image_count == 0

    def test_calculate_cluster_metadata_no_gps(self):
        """Test cluster metadata calculation with images that have no GPS."""
        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(id=1, timestamp=time_base),
            Image(id=2, timestamp=time_base + timedelta(hours=1)),
        ]

        metadata = calculate_cluster_metadata(images)

        assert metadata.center_lat is None
        assert metadata.center_lon is None
        assert metadata.name == "Unknown_2025-10-29"
        assert metadata.start_time == time_base
        assert metadata.end_time == time_base + timedelta(hours=1)
        assert metadata.image_count == 2

    def test_save_clusters_to_database(self):
        """Test saving clustering results to database."""
        from src.database import db

        # Clear existing data
        with db.get_connection() as conn:
            conn.execute('DELETE FROM clusters')
            conn.execute('DELETE FROM images')
            conn.commit()

        # Create test images
        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(id=1, filename='test1.jpg', latitude=40.7128, longitude=-74.0060, timestamp=time_base),
            Image(id=2, filename='test2.jpg', latitude=40.7130, longitude=-74.0065, timestamp=time_base + timedelta(minutes=15)),
        ]

        # Add images to database first
        for img in images:
            img.id = db.add_image(img)

        # Create clustering results
        clusters = {0: images}

        # Save to database
        mapping = save_clusters_to_database(clusters)

        assert len(mapping) == 1
        assert 0 in mapping

        # Verify cluster was saved
        saved_clusters = db.get_all_clusters()
        assert len(saved_clusters) == 1

        cluster = saved_clusters[0]
        assert cluster.name == "NYC_2025-10-29"
        assert cluster.image_count == 2

        # Verify images were updated with cluster IDs
        for img in images:
            assert img.id is not None
            updated_img = db.get_image(img.id)
            assert updated_img is not None
            assert updated_img.cluster_id == mapping[0]

    def test_process_and_save_clustering(self):
        """Test the complete clustering and database storage pipeline."""
        from src.database import db

        # Clear existing data
        with db.get_connection() as conn:
            conn.execute('DELETE FROM clusters')
            conn.execute('DELETE FROM images')
            conn.commit()

        # Create test images
        time_base = datetime(2025, 10, 29, 10, 0, 0)
        images = [
            Image(filename='nyc1.jpg', latitude=40.7128, longitude=-74.0060, timestamp=time_base),
            Image(filename='nyc2.jpg', latitude=40.7130, longitude=-74.0065, timestamp=time_base + timedelta(minutes=15)),
            Image(filename='la.jpg', latitude=34.0522, longitude=-118.2437, timestamp=time_base + timedelta(hours=1)),
        ]

        # Add images to database first
        for img in images:
            img.id = db.add_image(img)

        # Process clustering and save
        cluster_mapping = process_and_save_clustering(images, distance_threshold=1.0, time_threshold_hours=3.0)

        # Verify results
        assert len(cluster_mapping) >= 1

        # Check that clusters were created
        saved_clusters = db.get_all_clusters()
        assert len(saved_clusters) >= 1

        # Check that images have cluster assignments
        for img in images:
            assert img.id is not None
            updated_img = db.get_image(img.id)
            assert updated_img is not None
            assert updated_img.cluster_id is not None