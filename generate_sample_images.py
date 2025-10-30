#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "requests",
#     "pillow",
#     "piexif",
# ]
# ///
"""
generate_sample_images.py

Generates 500 sample images with metadata and augmentations.
Uses Lorem Picsum API for free random images.
"""

import os
import random
import requests
from PIL import Image, ImageFilter, ImageDraw
import json
from datetime import datetime, timedelta
import piexif

# Configuration
NUM_IMAGES = 500
OUTPUT_DIR = "Sample_Images"
IMAGE_SIZE = (800, 600)  # width, height

# GPS clusters: define some locations
GPS_CLUSTERS = [
    {"lat": 40.7128, "lon": -74.0060, "name": "New York"},  # NYC
    {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles"},  # LA
    {"lat": 41.8781, "lon": -87.6298, "name": "Chicago"},  # Chicago
    {"lat": 29.7604, "lon": -95.3698, "name": "Houston"},  # Houston
    {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix"},  # Phoenix
]

def fetch_image(url):
    """Fetch image from URL."""
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(requests.get(url, stream=True).raw)
    else:
        raise Exception(f"Failed to fetch image: {response.status_code}")

def add_noise(image, noise_type="blur"):
    """Add noise to image."""
    if noise_type == "blur":
        return image.filter(ImageFilter.BLUR)
    elif noise_type == "gaussian":
        # Simple noise addition
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for _ in range(100):  # Add some random pixels
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), color)
        return image
    else:
        return image

def augment_image(image):
    """Augment image: rotate, flip, etc."""
    augmentations = ["rotate", "flip", "mirror"]
    aug = random.choice(augmentations)
    if aug == "rotate":
        return image.rotate(random.randint(1, 359))
    elif aug == "flip":
        return image.transpose(Image.FLIP_TOP_BOTTOM)
    elif aug == "mirror":
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    return image

def generate_metadata(cluster, base_date, use_random_gps=False):
    """Generate GPS and datetime metadata."""
    if use_random_gps or random.random() < 0.05:  # 5% random GPS
        lat = random.uniform(-90, 90)
        lon = random.uniform(-180, 180)
    else:
        # Add some variation to GPS
        lat_var = random.uniform(-0.01, 0.01)
        lon_var = random.uniform(-0.01, 0.01)
        lat = cluster["lat"] + lat_var
        lon = cluster["lon"] + lon_var

    # Add time variation
    time_var = timedelta(hours=random.randint(-12, 12), minutes=random.randint(-30, 30))
    dt = base_date + time_var

    return lat, lon, dt

def create_exif(lat, lon, dt):
    """Create EXIF dict with GPS and datetime."""
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    # DateTimeOriginal
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt.strftime("%Y:%m:%d %H:%M:%S")

    # GPS
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = _deg_to_dms(abs(lat))
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = _deg_to_dms(abs(lon))

    return piexif.dump(exif_dict)

def _deg_to_dms(deg):
    """Convert degrees to DMS rational."""
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m/60) * 3600
    return ((d, 1), (m, 1), (int(s * 100), 100))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    base_date = datetime(2025, 10, 29, 12, 0, 0)  # Current date

    for i in range(NUM_IMAGES):
        print(f"Generating image {i+1}/{NUM_IMAGES}")

        # Fetch random image
        url = f"https://picsum.photos/{IMAGE_SIZE[0]}/{IMAGE_SIZE[1]}?random={i}"
        try:
            img = fetch_image(url)
        except Exception as e:
            print(f"Error fetching image {i}: {e}")
            continue

        # Choose cluster (some images in same cluster)
        cluster = random.choice(GPS_CLUSTERS)

        # Generate metadata
        lat, lon, dt = generate_metadata(cluster, base_date)

        # Decide if to augment
        is_augmented = random.random() < 0.2  # 20% augmented
        if is_augmented:
            img = augment_image(img)
            # Add noise to augmented
            img = add_noise(img, random.choice(["blur", "gaussian"]))

        # Add noise to some non-augmented (smaller sample)
        if not is_augmented and random.random() < 0.1:  # 10% of non-augmented
            img = add_noise(img, "blur")

        # Create EXIF
        exif_bytes = create_exif(lat, lon, dt)

        # Save image with EXIF
        filename = f"image_{i+1:03d}.jpg"
        filepath = os.path.join(OUTPUT_DIR, filename)

        img.save(filepath, "JPEG", exif=exif_bytes)

    print("Done!")

if __name__ == "__main__":
    main()