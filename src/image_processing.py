"""
Image processing utilities for the Smart Album Maker.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple

def detect_blur(image: Image.Image) -> float:
    """
    Calculate blur score for an image using Laplacian variance.

    Args:
        image: PIL Image object

    Returns:
        float: Blur score (0.0 = very blurry, 1.0 = sharp)
    """
    # Convert PIL image to numpy array
    img_array = np.array(image)

    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Compute Laplacian variance
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Normalize to 0-1 range (higher variance = sharper image)
    # Using a reasonable threshold - images with variance > 100 are considered sharp
    max_variance = 500.0  # Adjust based on testing
    score = min(laplacian_var / max_variance, 1.0)

    return score

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for analysis (resize, convert format, etc.).

    Args:
        image: PIL Image object

    Returns:
        PIL Image object: Preprocessed image
    """
    # Convert to RGB if not already
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Resize to standard size for consistent processing
    # Keep aspect ratio but limit max dimension to 1024px
    max_size = 1024
    width, height = image.size

    if width > height:
        if width > max_size:
            new_width = max_size
            new_height = int(height * max_size / width)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        if height > max_size:
            new_height = max_size
            new_width = int(width * max_size / height)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return image