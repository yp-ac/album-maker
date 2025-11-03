"""
Tests for graph-based duplicate detection functionality.
"""

import pytest
import tempfile
import os
from PIL import Image, ImageDraw
from unittest.mock import patch, MagicMock
import networkx as nx
import imagehash

from src.graph_duplicates import (
    calculate_perceptual_hash,
    calculate_hash_distance,
    build_similarity_graph,
    find_connected_duplicate_groups,
    detect_graph_based_duplicates,
    analyze_graph_structure
)
from src.models import Image as ImageModel
from src.database import Database

class TestPerceptualHashing:
    """Test perceptual hash calculation."""

    def test_calculate_perceptual_hash(self):
        """Test that perceptual hashes are calculated correctly."""
        # Create a test image
        img = Image.new('RGB', (100, 100), color='red')
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img.save(tmp.name)
            tmp_path = tmp.name

        try:
            hashes = calculate_perceptual_hash(tmp_path)

            # Should have all three hash types
            assert 'ahash' in hashes
            assert 'phash' in hashes
            assert 'dhash' in hashes

            # All hashes should be ImageHash objects
            assert isinstance(hashes['ahash'], imagehash.ImageHash)
            assert isinstance(hashes['phash'], imagehash.ImageHash)
            assert isinstance(hashes['dhash'], imagehash.ImageHash)

        finally:
            os.unlink(tmp_path)

    def test_calculate_hash_distance_identical(self):
        """Test hash distance for identical hashes."""
        hash_str = "0123456789abcdef"
        distance = calculate_hash_distance(hash_str, hash_str)
        assert distance == 0

    def test_calculate_hash_distance_different(self):
        """Test hash distance for different hashes."""
        hash1 = "0000000000000000"
        hash2 = "ffffffffffffffff"
        distance = calculate_hash_distance(hash1, hash2)
        # Should be maximum distance (64 bits all different)
        assert distance == 64

class TestGraphConstruction:
    """Test similarity graph construction."""

    def test_build_similarity_graph_empty(self):
        """Test graph construction with empty list."""
        graph = build_similarity_graph([])
        
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_build_similarity_graph_single_image(self):
        """Test graph construction with single image."""
        img = ImageModel(id=1, filename="test.jpg", hash="abcd1234")
        graph = build_similarity_graph([img])
        
        assert graph.number_of_nodes() == 1
        assert graph.number_of_edges() == 0

    def test_build_similarity_graph_similar_images(self):
        """Test graph construction with similar images."""
        # Create images with similar hashes (low distance)
        images = [
            ImageModel(id=1, filename="img1.jpg", hash="0000000000000000"),
            ImageModel(id=2, filename="img2.jpg", hash="0000000000000001"),  # Distance: 1
            ImageModel(id=3, filename="img3.jpg", hash="0000000000000003"),  # Distance: 2
        ]
        
        graph = build_similarity_graph(images, similarity_threshold=5)
        
        assert graph.number_of_nodes() == 3
        # Should have edges between similar images
        assert graph.number_of_edges() >= 2

    def test_build_similarity_graph_dissimilar_images(self):
        """Test graph construction with dissimilar images."""
        images = [
            ImageModel(id=1, filename="img1.jpg", hash="0000000000000000"),
            ImageModel(id=2, filename="img2.jpg", hash="ffffffffffffffff"),  # Very different
        ]
        
        graph = build_similarity_graph(images, similarity_threshold=5)
        
        assert graph.number_of_nodes() == 2
        # Should have no edges (too dissimilar)
        assert graph.number_of_edges() == 0

    def test_build_similarity_graph_with_weights(self):
        """Test that edges have correct weights."""
        images = [
            ImageModel(id=1, filename="img1.jpg", hash="0000000000000000"),
            ImageModel(id=2, filename="img2.jpg", hash="0000000000000001"),
        ]
        
        graph = build_similarity_graph(images, similarity_threshold=5)
        
        # Should have edge with weight
        assert graph.has_edge(1, 2)
        edge_data = graph.get_edge_data(1, 2)
        assert 'weight' in edge_data
        assert 'distance' in edge_data
        assert edge_data['distance'] == 1

class TestConnectedComponents:
    """Test connected component detection."""

    def test_find_connected_duplicate_groups_no_duplicates(self):
        """Test with no connected components (no duplicates)."""
        G = nx.Graph()
        G.add_node(1, image=ImageModel(id=1, filename="img1.jpg", blur_score=0.8))
        G.add_node(2, image=ImageModel(id=2, filename="img2.jpg", blur_score=0.7))
        # No edges
        
        groups = find_connected_duplicate_groups(G)
        
        # No groups with 2+ images
        assert len(groups) == 0

    def test_find_connected_duplicate_groups_single_group(self):
        """Test with one connected component."""
        G = nx.Graph()
        img1 = ImageModel(id=1, filename="img1.jpg", blur_score=0.9)
        img2 = ImageModel(id=2, filename="img2.jpg", blur_score=0.7)
        img3 = ImageModel(id=3, filename="img3.jpg", blur_score=0.8)
        
        G.add_node(1, image=img1)
        G.add_node(2, image=img2)
        G.add_node(3, image=img3)
        G.add_edge(1, 2)
        G.add_edge(2, 3)
        
        groups = find_connected_duplicate_groups(G)
        
        assert len(groups) == 1
        assert len(groups[0]) == 3
        # Should be sorted by blur score (highest first)
        assert groups[0][0].blur_score == 0.9

    def test_find_connected_duplicate_groups_multiple_groups(self):
        """Test with multiple disconnected components."""
        G = nx.Graph()
        
        # Group 1: images 1-2
        G.add_node(1, image=ImageModel(id=1, filename="img1.jpg", blur_score=0.9))
        G.add_node(2, image=ImageModel(id=2, filename="img2.jpg", blur_score=0.8))
        G.add_edge(1, 2)
        
        # Group 2: images 3-4-5
        G.add_node(3, image=ImageModel(id=3, filename="img3.jpg", blur_score=0.7))
        G.add_node(4, image=ImageModel(id=4, filename="img4.jpg", blur_score=0.6))
        G.add_node(5, image=ImageModel(id=5, filename="img5.jpg", blur_score=0.5))
        G.add_edge(3, 4)
        G.add_edge(4, 5)
        
        groups = find_connected_duplicate_groups(G)
        
        assert len(groups) == 2
        # Check group sizes
        group_sizes = sorted([len(g) for g in groups])
        assert group_sizes == [2, 3]

class TestGraphBasedDuplicateDetection:
    """Test complete graph-based duplicate detection pipeline."""

    def test_detect_graph_based_duplicates(self):
        """Test the complete graph-based duplicate detection pipeline."""
        # Create test database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            tmp_path = tmp.name

        try:
            db = Database(tmp_path)

            # Create test images with similar hashes
            images = [
                ImageModel(id=1, filename="img1.jpg", hash="0000000000000000", blur_score=0.9),
                ImageModel(id=2, filename="img2.jpg", hash="0000000000000001", blur_score=0.8),
                ImageModel(id=3, filename="img3.jpg", hash="0000000000000002", blur_score=0.7),
                ImageModel(id=4, filename="img4.jpg", hash="ffffffffffffffff", blur_score=0.95),  # Different
            ]

            # Add to database
            for img in images:
                img.id = db.add_image(img)

            # Run graph-based detection
            stats = detect_graph_based_duplicates(images, db, similarity_threshold=5)

            # Should find one duplicate group (images 1-3)
            assert stats["total_images"] == 4
            assert stats["duplicate_groups"] == 1
            assert stats["duplicates_marked"] == 2  # 2 images marked as duplicates
            assert stats["images_kept"] == 2  # 2 images kept (best from group + unique)

            # Verify database
            groups = db.get_all_duplicate_groups()
            assert len(groups) == 1

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

class TestGraphAnalysis:
    """Test graph structure analysis."""

    def test_analyze_graph_structure(self):
        """Test graph structure analysis."""
        G = nx.Graph()
        
        # Add some nodes and edges
        for i in range(5):
            G.add_node(i, image=ImageModel(id=i, filename=f"img{i}.jpg"))
        
        G.add_edge(0, 1)
        G.add_edge(1, 2)
        G.add_edge(3, 4)
        
        stats = analyze_graph_structure(G)
        
        assert stats["nodes"] == 5
        assert stats["edges"] == 3
        assert stats["connected_components"] == 2
        assert "density" in stats
        assert "largest_component_size" in stats
