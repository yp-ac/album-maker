import logging
from typing import List, Dict, Set, Tuple, Any
import networkx as nx
import imagehash
from PIL import Image as PILImage

from .models import Image, DuplicateGroup
from .database import Database

logger = logging.getLogger(__name__)

def calculate_perceptual_hash(image_path: str) -> Dict[str, imagehash.ImageHash]:
    try:
        img = PILImage.open(image_path)
        
        hashes = {
            'ahash': imagehash.average_hash(img),
            'phash': imagehash.phash(img),
            'dhash': imagehash.dhash(img),
        }
        
        img.close()
        logger.debug(f"Calculated hashes for {image_path}: {hashes}")
        return hashes
        
    except Exception as e:
        logger.error(f"Failed to calculate hash for {image_path}: {e}")
        raise

def calculate_hash_distance(hash1: str, hash2: str) -> int:
    try:
        # Convert hex strings back to ImageHash objects
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        
        # Calculate Hamming distance
        distance = h1 - h2
        return distance
        
    except Exception as e:
        logger.warning(f"Failed to calculate hash distance: {e}")
        return 999  # Large distance for invalid hashes

def build_similarity_graph(images: List[Image], similarity_threshold: int = 10) -> nx.Graph:
    logger.info(f"Building similarity graph for {len(images)} images (threshold: {similarity_threshold})")
    
    G = nx.Graph()
    
    # Add all images as nodes
    for img in images:
        G.add_node(img.id, image=img)
    
    # Compare all pairs and add edges for similar images
    edge_count = 0
    for i, img1 in enumerate(images):
        for img2 in images[i+1:]:
            if not img1.hash or not img2.hash:
                continue
                
            # Calculate hash distance
            distance = calculate_hash_distance(img1.hash, img2.hash)
            
            # Add edge if similar enough
            if distance <= similarity_threshold:
                # Weight is inverse of distance (higher weight = more similar)
                weight = 1.0 / (distance + 1)  # +1 to avoid division by zero
                G.add_edge(img1.id, img2.id, weight=weight, distance=distance)
                edge_count += 1
                logger.debug(f"Similar images: {img1.filename} <-> {img2.filename} (distance: {distance})")
    
    logger.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G

def find_connected_duplicate_groups(graph: nx.Graph) -> List[List[Image]]:
    logger.info("Finding connected components for duplicate groups...")
    
    # Find all connected components
    components = nx.connected_components(graph)
    
    duplicate_groups = []
    component_count = 0
    
    for component in components:
        # Only consider groups with 2+ images as duplicates
        if len(component) >= 2:
            # Get all images in this component
            group_images = [graph.nodes[node_id]['image'] for node_id in component]
            
            # Sort by blur score (best quality first)
            group_images.sort(key=lambda x: x.blur_score, reverse=True)
            
            duplicate_groups.append(group_images)
            component_count += 1
            
            logger.info(f"Duplicate group {component_count}: {len(group_images)} images, "
                       f"best blur score: {group_images[0].blur_score:.3f}")
    
    logger.info(f"Found {len(duplicate_groups)} duplicate groups via connected components")
    return duplicate_groups

def detect_graph_based_duplicates(images: List[Image], db: Database, 
                                 similarity_threshold: int = 10) -> Dict[str, int]:
    logger.info(f"Starting graph-based duplicate detection for {len(images)} images...")
    
    try:
        # Step 1: Calculate perceptual hashes if not already done
        logger.info("Ensuring all images have perceptual hashes...")
        for img in images:
            if not img.hash and img.filename:
                try:
                    hashes = calculate_perceptual_hash(img.filename)
                    # Use average hash as the primary hash
                    img.hash = str(hashes['ahash'])
                    logger.debug(f"Calculated hash for {img.filename}: {img.hash}")
                except Exception as e:
                    logger.warning(f"Could not calculate hash for {img.filename}: {e}")
                    img.hash = ""  # Mark as processed but failed
        
        # Step 2: Build similarity graph
        graph = build_similarity_graph(images, similarity_threshold)
        
        # Step 3: Find connected components (duplicate groups)
        duplicate_groups = find_connected_duplicate_groups(graph)
        
        # Step 4: Save duplicate groups to database
        logger.info("Saving duplicate groups to database...")
        group_id = 1
        duplicates_marked = 0
        
        for group_images in duplicate_groups:
            # Best image is already first (sorted by blur score)
            best_image = group_images[0]
            best_image.is_duplicate = False
            best_image.duplicate_group = group_id
            
            # Mark all others as duplicates
            duplicate_ids = []
            for img in group_images[1:]:
                img.is_duplicate = True
                img.duplicate_group = group_id
                duplicate_ids.append(img.id)
                duplicates_marked += 1
                
                # Update in database
                db.mark_as_duplicate(img.id or 0, group_id)
            
            # Save duplicate group
            dup_group = DuplicateGroup(
                id=group_id,
                best_image_id=best_image.id,
                image_ids=str(duplicate_ids)
            )
            db.save_duplicate_group(dup_group)
            
            logger.info(f"Saved duplicate group {group_id}: kept {best_image.filename}, "
                       f"marked {len(duplicate_ids)} as duplicates")
            group_id += 1
        
        stats = {
            "total_images": len(images),
            "graph_nodes": graph.number_of_nodes(),
            "graph_edges": graph.number_of_edges(),
            "duplicate_groups": len(duplicate_groups),
            "duplicates_marked": duplicates_marked,
            "images_kept": len(images) - duplicates_marked,
        }
        
        logger.info(f"Graph-based duplicate detection complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error in graph-based duplicate detection: {e}")
        raise

def analyze_graph_structure(graph: nx.Graph) -> Dict[str, Any]:
    stats = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "connected_components": nx.number_connected_components(graph),
        "density": nx.density(graph),
        "average_clustering": nx.average_clustering(graph) if graph.number_of_nodes() > 0 else 0,
    }
    
    # Find largest component
    if graph.number_of_nodes() > 0:
        largest_cc = max(nx.connected_components(graph), key=len)
        stats["largest_component_size"] = len(largest_cc)
    else:
        stats["largest_component_size"] = 0
    
    logger.info(f"Graph structure analysis: {stats}")
    return stats
