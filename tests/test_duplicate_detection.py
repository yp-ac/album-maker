"""
Tests for duplicate detection and blur filtering functionality.
"""

import pytest
import tempfile
import os
from PIL import Image, ImageFilter
from unittest.mock import patch

from src.duplicate_detection import (
    calculate_blur_scores,
    greedy_select_best_images,
    filter_blurred_duplicates,
    process_blur_filtering
)
from src.models import Image as ImageModel
from src.database import Database

class TestBlurDetection:
    """Test blur score calculation functionality."""

    def test_calculate_blur_scores_for_sharp_image(self):
        """Test blur score calculation for a sharp image."""
        # Create a sharp test image
        img = Image.new('RGB', (100, 100), color='white')
        # Add some high-frequency content to make it sharp
        for x in range(0, 100, 10):
            for y in range(0, 100, 10):
                img.putpixel((x, y), (0, 0, 0))

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img.save(tmp.name)
            tmp_path = tmp.name

        try:
            # Create image model
            image_model = ImageModel(filename=tmp_path, blur_score=0.0)

            # Calculate blur score
            result = calculate_blur_scores([image_model])

            # Should have calculated a blur score
            assert len(result) == 1
            assert result[0].blur_score > 0.0
            assert result[0].blur_score <= 1.0

        finally:
            os.unlink(tmp_path)

    def test_calculate_blur_scores_for_blurry_image(self):
        """Test blur score calculation for a blurry image."""
        # Create a sharp test image then blur it
        img = Image.new('RGB', (100, 100), color='white')
        # Add some high-frequency content
        for x in range(0, 100, 10):
            for y in range(0, 100, 10):
                img.putpixel((x, y), (0, 0, 0))

        # Apply blur filter
        blurry_img = img.filter(ImageFilter.GaussianBlur(radius=5))

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            blurry_img.save(tmp.name)
            tmp_path = tmp.name

        try:
            # Create image model
            image_model = ImageModel(filename=tmp_path, blur_score=0.0)

            # Calculate blur score
            result = calculate_blur_scores([image_model])

            # Should have calculated a blur score
            assert len(result) == 1
            assert result[0].blur_score >= 0.0
            assert result[0].blur_score <= 1.0

        finally:
            os.unlink(tmp_path)

class TestGreedySelection:
    """Test greedy selection algorithm for duplicate groups."""

    def test_greedy_select_best_images_no_duplicates(self):
        """Test greedy selection with no duplicates."""
        images = [
            ImageModel(id=1, filename="img1.jpg", hash="hash1", blur_score=0.8),
            ImageModel(id=2, filename="img2.jpg", hash="hash2", blur_score=0.7),
        ]

        result = greedy_select_best_images(images)

        # Should have no duplicate groups
        assert len(result) == 0

    def test_greedy_select_best_images_with_duplicates(self):
        """Test greedy selection with duplicate images."""
        images = [
            ImageModel(id=1, filename="img1.jpg", hash="same_hash", blur_score=0.6),
            ImageModel(id=2, filename="img2.jpg", hash="same_hash", blur_score=0.8),
            ImageModel(id=3, filename="img3.jpg", hash="same_hash", blur_score=0.4),
            ImageModel(id=4, filename="img4.jpg", hash="different_hash", blur_score=0.9),
        ]

        result = greedy_select_best_images(images)

        # Should have one duplicate group
        assert len(result) == 1
        assert 1 in result

        # Should select the sharpest image first
        group = result[1]
        assert len(group) == 3
        assert group[0].blur_score == 0.8  # Sharpest first
        assert group[1].blur_score == 0.6
        assert group[2].blur_score == 0.4

class TestBlurFiltering:
    """Test complete blur filtering pipeline."""

    def test_filter_blurred_duplicates(self):
        """Test the complete blur filtering pipeline."""
        # Create test database with temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            tmp_path = tmp.name

        try:
            db = Database(tmp_path)

            # Create test images with same hash (duplicates)
            images = [
                ImageModel(id=1, filename="sharp.jpg", hash="dup_hash", blur_score=0.8),
                ImageModel(id=2, filename="medium.jpg", hash="dup_hash", blur_score=0.6),
                ImageModel(id=3, filename="blurry.jpg", hash="dup_hash", blur_score=0.3),
                ImageModel(id=4, filename="unique.jpg", hash="unique_hash", blur_score=0.7),
            ]

            # Add images to database first
            for img in images:
                img.id = db.add_image(img)

            # Mock the blur score calculation since we're testing the logic
            with patch('src.duplicate_detection.calculate_blur_scores', return_value=images):
                result = filter_blurred_duplicates(images, db)

                # Should keep 2 images: 1 sharp duplicate + 1 unique
                assert len(result) == 2

                # Check that duplicates are marked
                duplicate_images = [img for img in result if img.is_duplicate]
                assert len(duplicate_images) == 0  # Best images are not marked as duplicates

                # Check that we have duplicate groups
                groups = db.get_all_duplicate_groups()
                assert len(groups) == 1

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_process_blur_filtering_pipeline(self):
        """Test the complete blur filtering processing pipeline."""
        # Create test database with temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            tmp_path = tmp.name

        try:
            db = Database(tmp_path)

            # Create test images
            images = [
                ImageModel(filename="img1.jpg", hash="hash1", blur_score=0.8),
                ImageModel(filename="img2.jpg", hash="hash1", blur_score=0.6),
                ImageModel(filename="img3.jpg", hash="hash2", blur_score=0.7),
            ]

            # Add images to database
            for img in images:
                img.id = db.add_image(img)

            # Mock blur calculation
            with patch('src.duplicate_detection.calculate_blur_scores', return_value=images):
                stats = process_blur_filtering(images, db)

                # Check statistics
                assert stats["original_images"] == 3
                assert stats["filtered_images"] == 2  # 1 duplicate group, 1 unique
                assert stats["duplicates_removed"] == 1
                assert stats["duplicate_groups"] == 1

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
