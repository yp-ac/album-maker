#!/usr/bin/env python3
"""
Manual Testing Script for User Story 3: Graph-Based Duplicate Detection

This script tests the graph-based duplicate detection by creating images with
varying levels of similarity and verifying that transitive duplicates are detected.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database import Database
from src.models import Image as ImageModel
from src.graph_duplicates import (
    calculate_perceptual_hash,
    build_similarity_graph,
    find_connected_duplicate_groups,
    detect_graph_based_duplicates,
    analyze_graph_structure
)
import networkx as nx

def create_test_images_for_graph():
    """
    Create test images demonstrating graph-based duplicate detection.
    
    Creates:
    - Transitive duplicates (A similar to B, B similar to C, forms one group)
    - Near-duplicates (cropped, rotated versions)
    - Exact duplicates
    - Unique images
    """
    test_dir = Path("test_graph_duplicates")
    test_dir.mkdir(exist_ok=True)

    print("Creating test images for graph-based duplicate detection...")
    test_images = []

    # === GROUP 1: Transitive Duplicates ===
    print("\n  Creating Group 1: Transitive duplicates (A→B→C)")
    
    # Image A: Original red square
    img_a = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(img_a)
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black', width=3)
    path_a = test_dir / "group1_original.jpg"
    img_a.save(path_a, quality=95)
    test_images.append((str(path_a), "Group 1: Original", 1.0))

    # Image B: Slightly modified (small blur)
    img_b = img_a.filter(ImageFilter.GaussianBlur(radius=0.5))
    path_b = test_dir / "group1_slight_blur.jpg"
    img_b.save(path_b, quality=95)
    test_images.append((str(path_b), "Group 1: Slight modification", 0.95))

    # Image C: More modified (medium blur)
    img_c = img_a.filter(ImageFilter.GaussianBlur(radius=1.5))
    path_c = test_dir / "group1_medium_blur.jpg"
    img_c.save(path_c, quality=95)
    test_images.append((str(path_c), "Group 1: Medium modification", 0.85))

    # === GROUP 2: Near-duplicates (cropped versions) ===
    print("  Creating Group 2: Near-duplicates (cropped)")
    
    # Image D: Original blue pattern
    img_d = Image.new('RGB', (200, 200), color='lightblue')
    draw = ImageDraw.Draw(img_d)
    for i in range(0, 200, 20):
        draw.line([(i, 0), (i, 200)], fill='darkblue', width=2)
        draw.line([(0, i), (200, i)], fill='darkblue', width=2)
    path_d = test_dir / "group2_full.jpg"
    img_d.save(path_d, quality=95)
    test_images.append((str(path_d), "Group 2: Full image", 1.0))

    # Image E: Cropped version (80% of original)
    img_e = img_d.crop((20, 20, 180, 180))
    img_e = img_e.resize((200, 200))  # Resize back to original size
    path_e = test_dir / "group2_cropped.jpg"
    img_e.save(path_e, quality=95)
    test_images.append((str(path_e), "Group 2: Cropped & resized", 0.9))

    # === GROUP 3: Rotated versions ===
    print("  Creating Group 3: Rotated versions")
    
    # Image F: Original green triangle
    img_f = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(img_f)
    draw.polygon([(100, 40), (40, 160), (160, 160)], fill='green', outline='black')
    path_f = test_dir / "group3_original.jpg"
    img_f.save(path_f, quality=95)
    test_images.append((str(path_f), "Group 3: Original orientation", 1.0))

    # Image G: Slightly rotated (5 degrees)
    img_g = img_f.rotate(5, fillcolor='white')
    path_g = test_dir / "group3_rotated_5deg.jpg"
    img_g.save(path_g, quality=95)
    test_images.append((str(path_g), "Group 3: Rotated 5°", 0.95))

    # === UNIQUE IMAGES (should NOT be grouped) ===
    print("  Creating unique images")
    
    # Image H: Completely different
    img_h = Image.new('RGB', (200, 200), color='yellow')
    draw = ImageDraw.Draw(img_h)
    draw.ellipse([50, 50, 150, 150], fill='purple')
    path_h = test_dir / "unique1.jpg"
    img_h.save(path_h, quality=95)
    test_images.append((str(path_h), "Unique image 1", 1.0))

    # Image I: Another unique image
    img_i = Image.new('RGB', (200, 200), color='orange')
    draw = ImageDraw.Draw(img_i)
    draw.text((50, 90), "UNIQUE", fill='white')
    path_i = test_dir / "unique2.jpg"
    img_i.save(path_i, quality=95)
    test_images.append((str(path_i), "Unique image 2", 1.0))

    print(f"Created {len(test_images)} test images in {test_dir}/")
    return test_images, test_dir

def test_graph_based_detection():
    """Test graph-based duplicate detection with various similarity scenarios."""
    print("\n" + "="*80)
    print("TESTING GRAPH-BASED DUPLICATE DETECTION - User Story 3")
    print("="*80)

    # Create test images
    test_images, test_dir = create_test_images_for_graph()

    # Calculate perceptual hashes
    print("\n" + "-"*60)
    print("CALCULATING PERCEPTUAL HASHES")
    print("-"*60)

    image_models = []
    for idx, (img_path, description, blur_score) in enumerate(test_images, 1):
        hashes = calculate_perceptual_hash(img_path)
        
        # Use average hash as primary hash
        hash_str = str(hashes['ahash'])
        
        print(f"{Path(img_path).name:25} | {description:35} | Hash: {hash_str[:16]}...")
        
        img_model = ImageModel(
            id=idx,  # Assign ID for graph nodes
            filename=img_path,
            hash=hash_str,
            blur_score=blur_score
        )
        image_models.append(img_model)

    # Build similarity graph
    print("\n" + "-"*60)
    print("BUILDING SIMILARITY GRAPH")
    print("-"*60)

    # Use different thresholds to show sensitivity
    thresholds = [5, 10, 15]
    
    for threshold in thresholds:
        print(f"\nThreshold: {threshold} bits")
        graph = build_similarity_graph(image_models, similarity_threshold=threshold)
        
        stats = analyze_graph_structure(graph)
        print(f"  Nodes: {stats['nodes']}")
        print(f"  Edges: {stats['edges']}")
        print(f"  Connected components: {stats['connected_components']}")
        print(f"  Largest component: {stats['largest_component_size']} images")
        print(f"  Graph density: {stats['density']:.3f}")

    # Use threshold=10 for detailed analysis
    threshold = 10
    print(f"\n{'='*60}")
    print(f"DETAILED ANALYSIS (threshold={threshold})")
    print("="*60)

    graph = build_similarity_graph(image_models, similarity_threshold=threshold)

    # Show edges
    print("\nSimilarity edges:")
    for edge in graph.edges(data=True):
        node1, node2, data = edge
        img1 = graph.nodes[node1]['image']
        img2 = graph.nodes[node2]['image']
        print(f"  {Path(img1.filename).name} <-> {Path(img2.filename).name} "
              f"(distance: {data['distance']}, weight: {data['weight']:.3f})")

    # Find duplicate groups
    print("\n" + "-"*60)
    print("DETECTING DUPLICATE GROUPS (Connected Components)")
    print("-"*60)

    duplicate_groups = find_connected_duplicate_groups(graph)

    print(f"\nFound {len(duplicate_groups)} duplicate groups:")
    for idx, group in enumerate(duplicate_groups, 1):
        print(f"\n  Group {idx}: {len(group)} images")
        for i, img in enumerate(group):
            marker = "✓ KEPT" if i == 0 else "✗ duplicate"
            print(f"    {marker} | {Path(img.filename).name:25} | Blur: {img.blur_score:.2f}")

    # Test with database
    print("\n" + "-"*60)
    print("COMPLETE PIPELINE WITH DATABASE")
    print("-"*60)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name

    try:
        db = Database(db_path)

        # Add images to database
        for img in image_models:
            img.id = db.add_image(img)

        # Run complete detection pipeline
        stats = detect_graph_based_duplicates(image_models, db, similarity_threshold=threshold)

        print(f"\nProcessing Statistics:")
        print(f"  Total images:        {stats['total_images']}")
        print(f"  Graph nodes:         {stats['graph_nodes']}")
        print(f"  Graph edges:         {stats['graph_edges']}")
        print(f"  Duplicate groups:    {stats['duplicate_groups']}")
        print(f"  Duplicates marked:   {stats['duplicates_marked']}")
        print(f"  Images kept:         {stats['images_kept']}")

        # Verify in database
        print("\n" + "-"*60)
        print("DATABASE VERIFICATION")
        print("-"*60)

        groups = db.get_all_duplicate_groups()
        print(f"\nDuplicate groups saved: {len(groups)}")

        for group in groups:
            if group.best_image_id:
                best_img = db.get_image(group.best_image_id)
                if best_img:
                    print(f"\n  Group {group.id}:")
                    print(f"    Best image: {Path(best_img.filename).name}")
                    print(f"    Blur score: {best_img.blur_score:.2f}")
                    print(f"    Duplicate count: {len(eval(group.image_ids))}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

    # Manual verification checklist
    print("\n" + "="*80)
    print("MANUAL VERIFICATION CHECKLIST")
    print("="*80)

    checklist = [
        ("Transitive duplicates detected",
         "Images A→B→C should form one connected group"),
        ("Near-duplicates grouped correctly",
         "Cropped/rotated versions should be in same group"),
        ("Unique images remain separate",
         "Unrelated images should not be grouped"),
        ("Best image selected per group",
         "Highest blur score image kept as representative"),
        ("Graph structure makes sense",
         "Number of edges and components should be reasonable"),
        ("Database integrity maintained",
         "All duplicate relationships stored correctly"),
    ]

    for idx, (check, description) in enumerate(checklist, 1):
        print(f"\n□ {idx}. {check}")
        print(f"   → {description}")

    print("\n" + "="*80)
    print("MANUAL TEST COMPLETE")
    print("="*80)
    print(f"\nTest images created in: {test_dir.absolute()}")
    print("Review the output above and verify the checklist items.")
    print("\nKey insight: Graph-based detection finds duplicates that simple")
    print("hash matching would miss (transitive relationships, near-duplicates)!")
    print("\nIf graph-based detection looks good, User Story 3 is ready for production!")

    # Cleanup
    keep_images = input("\nKeep test images for manual inspection? (y/N): ").lower().strip()
    if keep_images != 'y':
        shutil.rmtree(test_dir)
        print(f"Cleaned up test images from {test_dir}")

if __name__ == "__main__":
    test_graph_based_detection()
