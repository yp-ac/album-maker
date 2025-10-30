#!/usr/bin/env python3
"""
Script to print image data from the album maker database.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database import db
from src.models import Image

def print_image_data():
    """Print all image data from the database."""
    print("=== Album Maker Database - Image Data ===\n")

    images = db.get_all_images()

    if not images:
        print("No images found in database.")
        return

    print(f"Total images: {len(images)}\n")

    for i, img in enumerate(images, 1):
        print(f"Image {i}:")
        print(f"  ID: {img.id}")
        print(f"  Filename: {img.filename}")
        print(f"  GPS: ({img.latitude}, {img.longitude})" if img.latitude and img.longitude else "  GPS: Not available")
        print(f"  Timestamp: {img.timestamp}")
        print(f"  Blur Score: {img.blur_score:.3f}")
        print(f"  Hash: {img.hash[:16]}..." if img.hash else "  Hash: Not computed")
        print(f"  Cluster ID: {img.cluster_id}")
        print(f"  Is Duplicate: {img.is_duplicate}")
        print(f"  Duplicate Group: {img.duplicate_group}")
        print()

if __name__ == "__main__":
    print_image_data()