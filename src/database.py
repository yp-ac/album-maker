import sqlite3
import os
from typing import List, Optional
from datetime import datetime
from src.models import Image, Cluster, DuplicateGroup

DATABASE_PATH = "album_maker.db"

class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    timestamp DATETIME,
                    blur_score REAL DEFAULT 0.0,
                    hash TEXT,
                    cluster_id INTEGER,
                    is_duplicate BOOLEAN DEFAULT FALSE,
                    duplicate_group INTEGER,
                    FOREIGN KEY (cluster_id) REFERENCES clusters (id),
                    FOREIGN KEY (duplicate_group) REFERENCES duplicate_groups (id)
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    center_lat REAL,
                    center_lon REAL,
                    start_time DATETIME,
                    end_time DATETIME,
                    image_count INTEGER DEFAULT 0
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS duplicate_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    best_image_id INTEGER,
                    image_ids TEXT,
                    FOREIGN KEY (best_image_id) REFERENCES images (id)
                )
            ''')
            conn.commit()

    # Image operations
    def add_image(self, image: Image) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO images (filename, latitude, longitude, timestamp, blur_score, hash, cluster_id, is_duplicate, duplicate_group)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (image.filename, image.latitude, image.longitude, image.timestamp, image.blur_score, image.hash, image.cluster_id, image.is_duplicate, image.duplicate_group))
            conn.commit()
            return cursor.lastrowid or 0

    def get_image(self, image_id: int) -> Optional[Image]:
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM images WHERE id = ?', (image_id,)).fetchone()
            if row:
                return Image(*row)
            return None

    def get_all_images(self) -> List[Image]:
        with self.get_connection() as conn:
            rows = conn.execute('SELECT * FROM images').fetchall()
            return [Image(*row) for row in rows]

    def update_image_cluster(self, image_id: int, cluster_id: int):
        with self.get_connection() as conn:
            conn.execute('UPDATE images SET cluster_id = ? WHERE id = ?', (cluster_id, image_id))
            conn.commit()

    def update_image_blur_score(self, image_id: int, blur_score: float):
        with self.get_connection() as conn:
            conn.execute('UPDATE images SET blur_score = ? WHERE id = ?', (blur_score, image_id))
            conn.commit()

    def mark_as_duplicate(self, image_id: int, duplicate_group: int):
        with self.get_connection() as conn:
            conn.execute('UPDATE images SET is_duplicate = TRUE, duplicate_group = ? WHERE id = ?', (duplicate_group, image_id))
            conn.commit()

    def save_duplicate_group(self, group: DuplicateGroup) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO duplicate_groups (best_image_id, image_ids)
                VALUES (?, ?)
            ''', (group.best_image_id, group.image_ids))
            conn.commit()
            return cursor.lastrowid or 0

    # Cluster operations
    def add_cluster(self, cluster: Cluster) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO clusters (name, center_lat, center_lon, start_time, end_time, image_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (cluster.name, cluster.center_lat, cluster.center_lon, cluster.start_time, cluster.end_time, cluster.image_count))
            conn.commit()
            return cursor.lastrowid or 0

    def get_cluster(self, cluster_id: int) -> Optional[Cluster]:
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM clusters WHERE id = ?', (cluster_id,)).fetchone()
            if row:
                return Cluster(*row)
            return None

    def get_all_clusters(self) -> List[Cluster]:
        with self.get_connection() as conn:
            rows = conn.execute('SELECT * FROM clusters').fetchall()
            return [Cluster(*row) for row in rows]

    def update_cluster_image_count(self, cluster_id: int, count: int):
        with self.get_connection() as conn:
            conn.execute('UPDATE clusters SET image_count = ? WHERE id = ?', (count, cluster_id))
            conn.commit()

    # Duplicate group operations
    def add_duplicate_group(self, group: DuplicateGroup) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO duplicate_groups (best_image_id, image_ids)
                VALUES (?, ?)
            ''', (group.best_image_id, group.image_ids))
            conn.commit()
            return cursor.lastrowid

    def get_duplicate_group(self, group_id: int) -> Optional[DuplicateGroup]:
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM duplicate_groups WHERE id = ?', (group_id,)).fetchone()
            if row:
                return DuplicateGroup(*row)
            return None

    def get_all_duplicate_groups(self) -> List[DuplicateGroup]:
        with self.get_connection() as conn:
            rows = conn.execute('SELECT * FROM duplicate_groups').fetchall()
            return [DuplicateGroup(*row) for row in rows]

# Global database instance
db = Database()