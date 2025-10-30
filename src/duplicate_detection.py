import logging
from typing import List, Dict, Set
from collections import defaultdict

from .models import Image, DuplicateGroup
from .image_processing import detect_blur
from .database import Database

logger = logging.getLogger(__name__)

def calculate_blur_scores(images: List[Image]) -> List[Image]:
    updated_images = []

    for img in images:
        if img.blur_score == 0.0:  # Only calculate if not already done
            try:
                # Load image from file to calculate blur score
                from PIL import Image as PILImage
                pil_image = PILImage.open(img.filename)
                img.blur_score = detect_blur(pil_image)
                pil_image.close()
                logger.info(f"Calculated blur score for {img.filename}: {img.blur_score:.3f}")
            except Exception as e:
                logger.warning(f"Failed to calculate blur score for {img.filename}: {e}")
                img.blur_score = 0.5  # Default neutral score

        updated_images.append(img)

    return updated_images

def greedy_select_best_images(images: List[Image], similarity_threshold: float = 0.9) -> Dict[int, List[Image]]:
    # Group images by hash similarity (simplified - using exact hash match for now)
    hash_groups = defaultdict(list)

    for img in images:
        if img.hash:  # Only consider images with hashes
            hash_groups[img.hash].append(img)

    # Filter to groups with multiple images (actual duplicates)
    duplicate_groups = {}
    group_id = 1

    for hash_value, group_images in hash_groups.items():
        if len(group_images) > 1:
            # Sort by blur score (highest = sharpest first)
            sorted_images = sorted(group_images, key=lambda x: x.blur_score, reverse=True)

            duplicate_groups[group_id] = sorted_images
            group_id += 1

            logger.info(f"Found duplicate group {group_id-1}: {len(sorted_images)} images, "
                       f"best blur score: {sorted_images[0].blur_score:.3f}")

    return duplicate_groups

def filter_blurred_duplicates(images: List[Image], db: Database,
                            blur_threshold: float = 0.3) -> List[Image]:
    logger.info("Starting blur filtering and duplicate detection...")

    # Step 1: Calculate blur scores for all images
    images_with_blur = calculate_blur_scores(images)
    logger.info(f"Calculated blur scores for {len(images_with_blur)} images")

    # Step 2: Group duplicates and select best images
    duplicate_groups = greedy_select_best_images(images_with_blur)
    logger.info(f"Found {len(duplicate_groups)} duplicate groups")

    # Step 3: Mark duplicates and save to database
    filtered_images = []
    duplicate_group_id = 1

    for group_images in duplicate_groups.values():
        # Sort by blur score (highest first)
        sorted_group = sorted(group_images, key=lambda x: x.blur_score, reverse=True)

        # Keep the sharpest image
        best_image = sorted_group[0]
        best_image.is_duplicate = False
        best_image.duplicate_group = duplicate_group_id
        filtered_images.append(best_image)

        # Mark others as duplicates
        duplicate_image_ids = []
        for img in sorted_group[1:]:
            img.is_duplicate = True
            img.duplicate_group = duplicate_group_id
            duplicate_image_ids.append(img.id)

            # Update in database
            db.mark_as_duplicate(img.id or 0, duplicate_group_id)

        # Save duplicate group to database
        duplicate_group = DuplicateGroup(
            id=duplicate_group_id,
            best_image_id=best_image.id,
            image_ids=str(duplicate_image_ids)
        )
        db.save_duplicate_group(duplicate_group)

        logger.info(f"Duplicate group {duplicate_group_id}: kept {best_image.filename} "
                   f"(blur: {best_image.blur_score:.3f}), marked {len(duplicate_image_ids)} as duplicates")
        duplicate_group_id += 1

    # Step 4: Add non-duplicate images
    processed_hashes = set()
    for group_images in duplicate_groups.values():
        for img in group_images:
            processed_hashes.add(img.hash)

    for img in images_with_blur:
        if img.hash not in processed_hashes:
            filtered_images.append(img)

    logger.info(f"Blur filtering complete: {len(images)} -> {len(filtered_images)} images")

    return filtered_images

def process_blur_filtering(images: List[Image], db: Database,
                          blur_threshold: float = 0.3) -> Dict[str, int]:
    try:
        # Run blur filtering
        filtered_images = filter_blurred_duplicates(images, db, blur_threshold)

        # Update database with filtered results
        for img in filtered_images:
            if not img.is_duplicate:
                db.update_image_blur_score(img.id or 0, img.blur_score)

        stats = {
            "original_images": len(images),
            "filtered_images": len(filtered_images),
            "duplicates_removed": len(images) - len(filtered_images),
            "duplicate_groups": len([img for img in filtered_images if img.duplicate_group is not None])
        }

        logger.info(f"Blur filtering pipeline completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error in blur filtering pipeline: {e}")
        raise