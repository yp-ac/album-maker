#!/usr/bin/env python3
"""
Manual Testing Script for User Story 2: Blur Detection and Duplicate Filtering

This script tests the blur detection and greedy selection algorithm
by processing sample images with varying blur levels.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageFilter
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database import Database
from src.models import Image as ImageModel
from src.duplicate_detection import (
    calculate_blur_scores,
    greedy_select_best_images,
    filter_blurred_duplicates,
    process_blur_filtering
)
from src.image_processing import detect_blur
import imagehash

def create_test_images_with_blur():
    """
    Create a set of test images with varying blur levels.
    Returns list of (filepath, blur_level_description) tuples.
    """
    test_dir = Path("test_blur_images")
    test_dir.mkdir(exist_ok=True)

    print("Creating test images with varying blur levels...")

    # Create a sharp base image
    base_img = Image.new('RGB', (400, 400), color='white')
    
    # Add high-frequency content (makes blur more visible)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base_img)
    
    # Draw a pattern
    for x in range(0, 400, 20):
        draw.line([(x, 0), (x, 400)], fill='black', width=2)
    for y in range(0, 400, 20):
        draw.line([(0, y), (400, y)], fill='black', width=2)
    
    # Add some circles
    draw.ellipse([100, 100, 150, 150], fill='red')
    draw.ellipse([250, 100, 300, 150], fill='blue')
    draw.ellipse([100, 250, 150, 300], fill='green')
    draw.ellipse([250, 250, 300, 300], fill='yellow')

    test_images = []

    # Save sharp version
    sharp_path = test_dir / "image_sharp.jpg"
    base_img.save(sharp_path, quality=95)
    test_images.append((str(sharp_path), "Sharp (original)"))

    # Save slightly blurred version
    slightly_blurred = base_img.filter(ImageFilter.GaussianBlur(radius=1))
    slight_blur_path = test_dir / "image_slight_blur.jpg"
    slightly_blurred.save(slight_blur_path, quality=95)
    test_images.append((str(slight_blur_path), "Slight blur (radius=1)"))

    # Save moderately blurred version
    medium_blurred = base_img.filter(ImageFilter.GaussianBlur(radius=3))
    medium_blur_path = test_dir / "image_medium_blur.jpg"
    medium_blurred.save(medium_blur_path, quality=95)
    test_images.append((str(medium_blur_path), "Medium blur (radius=3)"))

    # Save heavily blurred version
    heavy_blurred = base_img.filter(ImageFilter.GaussianBlur(radius=8))
    heavy_blur_path = test_dir / "image_heavy_blur.jpg"
    heavy_blurred.save(heavy_blur_path, quality=95)
    test_images.append((str(heavy_blur_path), "Heavy blur (radius=8)"))

    # Create a second set of duplicates (different image content)
    base_img2 = Image.new('RGB', (400, 400), color='lightblue')
    draw2 = ImageDraw.Draw(base_img2)
    draw2.rectangle([50, 50, 350, 350], fill='orange', outline='purple', width=5)
    draw2.text((150, 180), "TEST", fill='white')

    sharp_path2 = test_dir / "image2_sharp.jpg"
    base_img2.save(sharp_path2, quality=95)
    test_images.append((str(sharp_path2), "Second image - Sharp"))

    blurred2 = base_img2.filter(ImageFilter.GaussianBlur(radius=5))
    blur_path2 = test_dir / "image2_blurred.jpg"
    blurred2.save(blur_path2, quality=95)
    test_images.append((str(blur_path2), "Second image - Blurred (radius=5)"))

    # Create a unique image (no duplicates)
    unique_img = Image.new('RGB', (400, 400), color='pink')
    draw3 = ImageDraw.Draw(unique_img)
    for i in range(0, 400, 40):
        draw3.ellipse([i, i, i+30, i+30], fill='purple')

    unique_path = test_dir / "image_unique.jpg"
    unique_img.save(unique_path, quality=95)
    test_images.append((str(unique_path), "Unique image"))

    print(f"Created {len(test_images)} test images in {test_dir}/")
    return test_images, test_dir

def calculate_image_hashes(image_paths):
    """Calculate perceptual hashes for images."""
    print("\nCalculating perceptual hashes...")
    hashes = {}
    for path, description in image_paths:
        img = Image.open(path)
        # Use average hash for duplicate detection
        img_hash = str(imagehash.average_hash(img))
        hashes[path] = img_hash
        print(f"  {Path(path).name}: hash={img_hash}")
        img.close()
    return hashes

def test_blur_detection():
    """Test blur detection on images with varying blur levels."""
    print("\n" + "="*80)
    print("TESTING BLUR DETECTION - User Story 2")
    print("="*80)

    # Create test images
    test_images, test_dir = create_test_images_with_blur()

    # Calculate blur scores
    print("\n" + "-"*60)
    print("BLUR SCORE CALCULATION")
    print("-"*60)

    blur_scores = []
    for img_path, description in test_images:
        img = Image.open(img_path)
        blur_score = detect_blur(img)
        blur_scores.append((img_path, description, blur_score))
        print(f"{Path(img_path).name:25} | {description:30} | Blur Score: {blur_score:.4f}")
        img.close()

    # Calculate hashes
    hashes = calculate_image_hashes(test_images)

    # Create ImageModel objects
    print("\n" + "-"*60)
    print("CREATING DATABASE ENTRIES")
    print("-"*60)

    # Use temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name

    try:
        db = Database(db_path)

        image_models = []
        for img_path, description in test_images:
            img = Image.open(img_path)
            blur_score = detect_blur(img)
            img_hash = hashes[img_path]
            img.close()

            img_model = ImageModel(
                filename=img_path,
                blur_score=blur_score,
                hash=img_hash
            )
            img_model.id = db.add_image(img_model)
            image_models.append(img_model)

        print(f"Added {len(image_models)} images to database")

        # Test greedy selection
        print("\n" + "-"*60)
        print("GREEDY SELECTION FOR DUPLICATE GROUPS")
        print("-"*60)

        duplicate_groups = greedy_select_best_images(image_models)

        print(f"\nFound {len(duplicate_groups)} duplicate groups:")
        for group_id, group_images in duplicate_groups.items():
            print(f"\n  Group {group_id}: {len(group_images)} images")
            for idx, img in enumerate(group_images):
                marker = "✓ BEST" if idx == 0 else "  duplicate"
                print(f"    {marker} | {Path(img.filename).name:25} | Blur: {img.blur_score:.4f} | Hash: {img.hash[:8]}...")

        # Test blur filtering pipeline
        print("\n" + "-"*60)
        print("BLUR FILTERING PIPELINE")
        print("-"*60)

        stats = process_blur_filtering(image_models, db)

        print(f"\nProcessing Statistics:")
        print(f"  Original images:     {stats['original_images']}")
        print(f"  Filtered images:     {stats['filtered_images']}")
        print(f"  Duplicates removed:  {stats['duplicates_removed']}")
        print(f"  Duplicate groups:    {stats['duplicate_groups']}")

        # Verify results
        print("\n" + "-"*60)
        print("VERIFICATION")
        print("-"*60)

        all_groups = db.get_all_duplicate_groups()
        print(f"\nDuplicate groups in database: {len(all_groups)}")

        for group in all_groups:
            best_img = db.get_image(group.best_image_id)
            print(f"\n  Group {group.id}:")
            print(f"    Best image: {Path(best_img.filename).name}")
            print(f"    Blur score: {best_img.blur_score:.4f}")
            print(f"    Hash: {best_img.hash}")

        # Manual verification checklist
        print("\n" + "="*80)
        print("MANUAL VERIFICATION CHECKLIST")
        print("="*80)

        checklist = [
            ("Blur scores decrease with blur level", 
             "Check that sharp images have higher scores than blurred ones"),
            ("Duplicate groups identified correctly",
             "Images with same content but different blur should be grouped"),
            ("Sharpest image selected as best",
             "Each group should keep the image with highest blur score"),
            ("Unique images not marked as duplicates",
             "Images with unique content should remain separate"),
            ("Database integrity maintained",
             "All duplicate relationships properly stored"),
        ]

        for idx, (check, description) in enumerate(checklist, 1):
            print(f"\n□ {idx}. {check}")
            print(f"   → {description}")

        print("\n" + "="*80)
        print("MANUAL TEST COMPLETE")
        print("="*80)
        print(f"\nTest images created in: {test_dir.absolute()}")
        print("Review the output above and verify the checklist items.")
        print("If blur filtering looks good, User Story 2 is ready for production!")

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        
        # Optionally keep test images for manual inspection
        keep_images = input("\nKeep test images for manual inspection? (y/N): ").lower().strip()
        if keep_images != 'y':
            shutil.rmtree(test_dir)
            print(f"Cleaned up test images from {test_dir}")

if __name__ == "__main__":
    test_blur_detection()
