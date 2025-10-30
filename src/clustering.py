import math
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta
from src.models import Image, Cluster
from src.error_handling import logger

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Convert degrees to radians
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Earth radius in kilometers
    earth_radius = 6371.0

    return c * earth_radius

def calculate_gps_distance(image1: Image, image2: Image) -> float:
    if (image1.latitude is None or image1.longitude is None or
        image2.latitude is None or image2.longitude is None):
        return float('inf')

    try:
        return haversine_distance(
            image1.latitude, image1.longitude,
            image2.latitude, image2.longitude
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"Error calculating GPS distance: {e}")
        return float('inf')

def calculate_time_difference(image1: Image, image2: Image) -> float:
    if image1.timestamp is None or image2.timestamp is None:
        return float('inf')

    try:
        # Calculate absolute time difference
        time_diff = abs(image1.timestamp - image2.timestamp)
        # Convert to hours
        return time_diff.total_seconds() / 3600.0
    except (TypeError, AttributeError) as e:
        logger.warning(f"Error calculating time difference: {e}")
        return float('inf')

def are_images_proximate(image1: Image, image2: Image,
                        distance_threshold: float = 1.0,
                        time_threshold_hours: float = 2.0) -> bool:
    gps_distance = calculate_gps_distance(image1, image2)
    time_diff_hours = calculate_time_difference(image1, image2)

    # Check if both GPS and time are within thresholds
    gps_ok = gps_distance <= distance_threshold
    time_ok = time_diff_hours <= time_threshold_hours

    return gps_ok and time_ok

def find_proximate_images(images: List[Image],
                         distance_threshold: float = 1.0,
                         time_threshold_hours: float = 2.0) -> List[Tuple[int, int]]:
    proximate_pairs = []

    # Compare each pair of images
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            if are_images_proximate(images[i], images[j],
                                  distance_threshold, time_threshold_hours):
                proximate_pairs.append((images[i].id, images[j].id))

    return proximate_pairs

def combined_distance(image1: Image, image2: Image,
                     distance_weight: float = 0.6,
                     time_weight: float = 0.4) -> float:

    gps_dist = calculate_gps_distance(image1, image2)
    time_diff = calculate_time_difference(image1, image2)

    # Normalize distances (handle infinity values)
    if gps_dist == float('inf'):
        gps_dist = 1000.0  # Large distance for missing GPS
    if time_diff == float('inf'):
        time_diff = 1000.0  # Large time difference for missing timestamps

    # Normalize to 0-1 range (rough approximation)
    # GPS: 0-10km maps to 0-1
    normalized_gps = min(gps_dist / 10.0, 1.0)
    # Time: 0-24hours maps to 0-1
    normalized_time = min(time_diff / 24.0, 1.0)

    # Weighted combination
    combined = (distance_weight * normalized_gps) + (time_weight * normalized_time)
    return combined

def hierarchical_cluster_images(images: List[Image],
                               distance_threshold: float = 0.3,
                               max_clusters: Optional[int] = None) -> Dict[int, List[Image]]:
    if not images:
        return {}

    if len(images) == 1:
        return {0: images}

    # Initialize each image as its own cluster
    clusters = {i: [img] for i, img in enumerate(images)}
    cluster_id_counter = len(images)

    # Calculate initial distance matrix
    distances = {}
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            dist = combined_distance(images[i], images[j])
            distances[(i, j)] = dist
            distances[(j, i)] = dist

    # Hierarchical clustering using single linkage
    while len(clusters) > 1:
        # Find closest pair of clusters
        min_distance = float('inf')
        closest_pair = None

        for cid1 in clusters:
            for cid2 in clusters:
                if cid1 >= cid2:
                    continue

                # Find minimum distance between any images in the two clusters
                cluster_dist = float('inf')
                for img1 in clusters[cid1]:
                    for img2 in clusters[cid2]:
                        idx1 = images.index(img1)
                        idx2 = images.index(img2)
                        dist = distances.get((idx1, idx2), float('inf'))
                        cluster_dist = min(cluster_dist, dist)

                if cluster_dist < min_distance:
                    min_distance = cluster_dist
                    closest_pair = (cid1, cid2)

        # Stop if minimum distance exceeds threshold
        if min_distance > distance_threshold:
            break

        # Stop if we've reached max_clusters
        if max_clusters and len(clusters) <= max_clusters:
            break

        # Merge closest clusters
        if closest_pair:
            cid1, cid2 = closest_pair
            # Merge cluster cid2 into cid1
            clusters[cid1].extend(clusters[cid2])
            del clusters[cid2]

    # Convert cluster dict to final format with consecutive IDs
    result = {}
    for new_id, (old_id, cluster_images) in enumerate(clusters.items()):
        result[new_id] = cluster_images

    logger.info(f"Hierarchical clustering completed: {len(images)} images -> {len(result)} clusters")
    return result

def cluster_images(images: List[Image],
                  distance_threshold: float = 1.0,
                  time_threshold_hours: float = 2.0) -> Dict[int, List[Image]]:
    if not images:
        logger.warning("No images provided for clustering")
        return {}

    # Use hierarchical clustering with combined distance metric
    # Convert distance/time thresholds to combined threshold
    # Rough conversion: distance_threshold=1km, time_threshold=2h -> combined ~0.3
    combined_threshold = min(distance_threshold / 10.0 + time_threshold_hours / 24.0, 1.0) * 0.5

    clusters = hierarchical_cluster_images(images, combined_threshold)

    # Ensure we have at least cluster 0 for outliers
    if not clusters:
        clusters[0] = []

    # Add any unclustered images to cluster 0
    clustered_image_ids = set()
    for cluster_images in clusters.values():
        clustered_image_ids.update(img.id for img in cluster_images)

    outliers = [img for img in images if img.id not in clustered_image_ids]
    if outliers:
        if 0 not in clusters:
            clusters[0] = []
        clusters[0].extend(outliers)
        logger.info(f"Added {len(outliers)} outlier images to cluster 0")

    logger.info(f"Clustering completed: {len(images)} images in {len(clusters)} clusters")
    return clusters

def calculate_cluster_metadata(images: List[Image]) -> Cluster:
    if not images:
        return Cluster()

    # Calculate center coordinates
    valid_coords = [(img.latitude, img.longitude) for img in images
                   if img.latitude is not None and img.longitude is not None]

    if valid_coords:
        avg_lat = sum(lat for lat, lon in valid_coords) / len(valid_coords)
        avg_lon = sum(lon for lat, lon in valid_coords) / len(valid_coords)
        center_lat, center_lon = avg_lat, avg_lon
    else:
        center_lat, center_lon = None, None

    # Calculate time range
    valid_times = [img.timestamp for img in images if img.timestamp is not None]
    if valid_times:
        start_time = min(valid_times)
        end_time = max(valid_times)
    else:
        start_time, end_time = None, None

    # Generate cluster name
    if center_lat is not None and center_lon is not None:
        # Simple location-based naming (could be enhanced with reverse geocoding)
        if abs(center_lat - 40.7128) < 1 and abs(center_lon - (-74.0060)) < 1:
            location_name = "NYC"
        elif abs(center_lat - 34.0522) < 1 and abs(center_lon - (-118.2437)) < 1:
            location_name = "LA"
        else:
            location_name = ".1f"
    else:
        location_name = "Unknown"

    if start_time:
        date_str = start_time.strftime("%Y-%m-%d")
        name = f"{location_name}_{date_str}"
    else:
        name = f"{location_name}_cluster"

    return Cluster(
        name=name,
        center_lat=center_lat,
        center_lon=center_lon,
        start_time=start_time,
        end_time=end_time,
        image_count=len(images)
    )

def save_clusters_to_database(clusters: Dict[int, List[Image]]) -> Dict[int, int]:
    from src.database import db

    cluster_id_mapping = {}

    for cluster_id, images in clusters.items():
        # Calculate cluster metadata
        cluster_metadata = calculate_cluster_metadata(images)

        # Save cluster to database
        db_cluster_id = db.add_cluster(cluster_metadata)
        cluster_id_mapping[cluster_id] = db_cluster_id

        # Update all images in this cluster
        for image in images:
            db.update_image_cluster(int(image.id or 0), db_cluster_id)

        logger.info(f"Saved cluster {cluster_id} -> DB ID {db_cluster_id} with {len(images)} images")

    return cluster_id_mapping

def process_and_save_clustering(images: List[Image],
                               distance_threshold: float = 1.0,
                               time_threshold_hours: float = 2.0) -> Dict[int, int]:
    logger.info(f"Starting clustering pipeline for {len(images)} images")

    # Perform clustering
    clusters = cluster_images(images, distance_threshold, time_threshold_hours)

    # Save to database
    cluster_mapping = save_clusters_to_database(clusters)

    logger.info(f"Clustering pipeline completed: {len(clusters)} clusters saved to database")
    return cluster_mapping