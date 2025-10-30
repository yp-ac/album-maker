#!/usr/bin/env python3
"""Debug script to check database contents."""

import sqlite3
from pathlib import Path

db_path = Path("album_maker.db")

if not db_path.exists():
    print("❌ Database file not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check images
cursor.execute("SELECT COUNT(*) FROM images")
image_count = cursor.fetchone()[0]
print(f"📸 Images in DB: {image_count}")

# Check clusters
cursor.execute("SELECT COUNT(*) FROM clusters")
cluster_count = cursor.fetchone()[0]
print(f"🗺️ Clusters in DB: {cluster_count}")

# Show first few clusters
if cluster_count > 0:
    cursor.execute("SELECT * FROM clusters LIMIT 5")
    clusters = cursor.fetchall()
    print(f"\n📋 First {len(clusters)} clusters:")
    for cluster in clusters:
        print(f"  ID={cluster[0]}, Name={cluster[1]}, Images={cluster[2]}")

# Check how many images have cluster_id set
cursor.execute("SELECT COUNT(*) FROM images WHERE cluster_id IS NOT NULL")
images_with_clusters = cursor.fetchone()[0]
print(f"\n🔗 Images with cluster_id: {images_with_clusters}/{image_count}")

# Check distribution
if images_with_clusters > 0:
    cursor.execute("SELECT cluster_id, COUNT(*) FROM images WHERE cluster_id IS NOT NULL GROUP BY cluster_id")
    distribution = cursor.fetchall()
    print(f"\n📊 Cluster distribution:")
    for cluster_id, count in distribution[:10]:
        print(f"  Cluster {cluster_id}: {count} images")

conn.close()
