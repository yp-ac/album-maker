"""
Smart Album Maker - Streamlit Web Application

A beautiful web interface for automatic photo organization using:
- GPS/Time-based clustering
- Blur detection and filtering
- Graph-based duplicate detection
"""

import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Import our algorithms
from src.database import Database
from src.models import Image as ImageModel
from src.clustering import process_and_save_clustering
from src.duplicate_detection import process_blur_filtering
from src.graph_duplicates import detect_graph_based_duplicates, calculate_perceptual_hash
from src.image_processing import detect_blur
import imagehash

# Page configuration
st.set_page_config(
    page_title="Smart Album Maker",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'db' not in st.session_state:
    # Initialize database connection (persistent across sessions)
    db_path = Path("album_maker.db")
    st.session_state.db = Database(str(db_path))
if 'images' not in st.session_state:
    st.session_state.images = []
if 'stats' not in st.session_state:
    st.session_state.stats = {}

def load_images_from_upload(uploaded_files):
    """Load uploaded images and extract metadata."""
    images = []
    temp_dir = Path(tempfile.mkdtemp())
    exif_errors = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, uploaded_file in enumerate(uploaded_files):
        # Save uploaded file temporarily
        file_path = temp_dir / uploaded_file.name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Create image model
        img_model = ImageModel(filename=str(file_path))
        
        # Try to extract EXIF data
        try:
            from PIL.ExifTags import TAGS, GPSTAGS
            pil_image = Image.open(file_path)
            exif = pil_image.getexif()
            
            if exif:
                # Extract DateTime from Exif IFD (not main EXIF!)
                try:
                    exif_ifd = exif.get_ifd(0x8769)  # Exif IFD tag
                    if exif_ifd:
                        for tag_id, value in exif_ifd.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == "DateTimeOriginal" or tag == "DateTime":
                                try:
                                    # Handle bytes or string
                                    dt_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                                    img_model.timestamp = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                                    break
                                except:
                                    pass
                except:
                    pass
                
                # Extract GPS from GPS IFD
                try:
                    gps_ifd = exif.get_ifd(0x8825)  # GPS IFD tag
                    if gps_ifd:
                        gps_data = {}
                        for gps_tag_id, value in gps_ifd.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = value
                        
                        # Parse GPS coordinates
                        if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                            lat = gps_data['GPSLatitude']
                            lon = gps_data['GPSLongitude']
                            lat_ref = gps_data.get('GPSLatitudeRef', b'N')
                            lon_ref = gps_data.get('GPSLongitudeRef', b'E')
                            
                            # Handle bytes
                            if isinstance(lat_ref, bytes):
                                lat_ref = lat_ref.decode('utf-8')
                            if isinstance(lon_ref, bytes):
                                lon_ref = lon_ref.decode('utf-8')
                            
                            # Convert rational tuples to decimal (ensure float conversion)
                            lat_decimal = float(lat[0]) + float(lat[1])/60 + float(lat[2])/3600
                            lon_decimal = float(lon[0]) + float(lon[1])/60 + float(lon[2])/3600
                            
                            img_model.latitude = float(lat_decimal * (-1 if lat_ref == 'S' else 1))
                            img_model.longitude = float(lon_decimal * (-1 if lon_ref == 'W' else 1))
                except:
                    pass
            
            pil_image.close()
            
        except Exception as e:
            # Count EXIF errors silently instead of showing each warning
            exif_errors += 1
        
        images.append(img_model)
        
        # Update progress
        progress = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        status_text.text(f"Loading images... {idx + 1}/{len(uploaded_files)}")
    
    progress_bar.empty()
    status_text.empty()
    
    # Show summary of EXIF errors if any
    if exif_errors > 0:
        st.info(f"ℹ️ {exif_errors} image(s) missing EXIF data - will use defaults for GPS/timestamp")
    
    return images, temp_dir

def process_images(images, db, config):
    """Run all processing algorithms on images."""
    all_stats = {}
    
    # Step 1: Save images to database
    st.info("💾 Saving images to database...")
    for img in images:
        img.id = db.add_image(img)
    
    # Step 2: GPS/Time Clustering
    if config['enable_clustering']:
        st.info("🗺️ Running GPS/Time clustering...")
        cluster_mapping = process_and_save_clustering(
            images,
            distance_threshold=config['distance_threshold'],
            time_threshold_hours=config['time_threshold']
        )
        num_clusters = len(set(cluster_mapping.values()))
        all_stats['clustering'] = {'num_clusters': num_clusters, 'mapping': cluster_mapping}
        st.success(f"✅ Created {num_clusters} clusters!")
    
    # Step 3: Calculate blur scores and hashes
    st.info("🔍 Analyzing image quality and calculating hashes...")
    progress_bar = st.progress(0)
    for idx, img in enumerate(images):
        try:
            pil_image = Image.open(img.filename)
            
            # Calculate blur score
            img.blur_score = detect_blur(pil_image)
            
            # Calculate perceptual hash
            hashes = calculate_perceptual_hash(img.filename)
            img.hash = str(hashes['ahash'])
            
            # Update database
            db.update_image_blur_score(img.id, img.blur_score)
            
            pil_image.close()
            progress_bar.progress((idx + 1) / len(images))
        except Exception as e:
            st.warning(f"Error processing {img.filename}: {e}")
    
    progress_bar.empty()
    
    # Step 4: Blur filtering (simple hash-based duplicates)
    if config['enable_blur_filter']:
        st.info("🎯 Filtering blurred duplicates...")
        blur_stats = process_blur_filtering(images, db, blur_threshold=config['blur_threshold'])
        all_stats['blur_filtering'] = blur_stats
        st.success(f"✅ Removed {blur_stats['duplicates_removed']} blurred duplicates!")
    
    # Step 5: Graph-based duplicate detection
    if config['enable_graph_duplicates']:
        st.info("🕸️ Running graph-based duplicate detection...")
        graph_stats = detect_graph_based_duplicates(
            images, db, 
            similarity_threshold=config['similarity_threshold']
        )
        all_stats['graph_duplicates'] = graph_stats
        st.success(f"✅ Found {graph_stats['duplicate_groups']} duplicate groups via graph analysis!")
    
    return all_stats

def main():
    # Header
    st.title("📸 Smart Album Maker")
    st.markdown("*Intelligent photo organization using advanced algorithms*")
    st.markdown("---")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("🗺️ GPS/Time Clustering")
        enable_clustering = st.checkbox("Enable clustering", value=True)
        distance_threshold = st.slider(
            "Distance threshold (km)",
            min_value=0.1, max_value=10.0, value=1.0, step=0.1,
            disabled=not enable_clustering
        )
        time_threshold = st.slider(
            "Time threshold (hours)",
            min_value=0.5, max_value=24.0, value=3.0, step=0.5,
            disabled=not enable_clustering
        )
        
        st.subheader("🎯 Blur Filtering")
        enable_blur_filter = st.checkbox("Enable blur filtering", value=True)
        blur_threshold = st.slider(
            "Blur threshold",
            min_value=0.0, max_value=1.0, value=0.3, step=0.05,
            disabled=not enable_blur_filter
        )
        
        st.subheader("🕸️ Graph-Based Duplicates")
        enable_graph_duplicates = st.checkbox("Enable graph duplicates", value=True)
        similarity_threshold = st.slider(
            "Similarity threshold (bits)",
            min_value=1, max_value=20, value=10, step=1,
            disabled=not enable_graph_duplicates
        )
        
    # Main content
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📊 Results", "🖼️ Gallery"])
    
    with tab1:
        st.header("Upload Your Photos")
        
        uploaded_files = st.file_uploader(
            "Choose image files (JPG, PNG)",
            type=['jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            help="Upload multiple photos to organize"
        )
        
        if uploaded_files:
            st.success(f"✅ Uploaded {len(uploaded_files)} images")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Process Images", use_container_width=True):
                    with st.spinner("Processing your photos..."):
                        # Load images
                        images, temp_dir = load_images_from_upload(uploaded_files)
                        
                        # Use existing database from session state
                        db = st.session_state.db
                        
                        # Process images
                        config = {
                            'enable_clustering': enable_clustering,
                            'distance_threshold': distance_threshold,
                            'time_threshold': time_threshold,
                            'enable_blur_filter': enable_blur_filter,
                            'blur_threshold': blur_threshold,
                            'enable_graph_duplicates': enable_graph_duplicates,
                            'similarity_threshold': similarity_threshold,
                        }
                        
                        stats = process_images(images, db, config)
                        
                        # Save to session state
                        st.session_state.processed = True
                        st.session_state.db = db
                        st.session_state.images = images
                        st.session_state.stats = stats
                        st.session_state.temp_dir = temp_dir
                        
                        st.success("🎉 Processing complete!")
                        st.balloons()
    
    with tab2:
        st.header("Processing Results")
        
        if not st.session_state.processed:
            st.info("👈 Upload and process images first!")
        else:
            stats = st.session_state.stats
            images = st.session_state.images
            db = st.session_state.db
            
            # Summary metrics
            st.subheader("📈 Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Images", len(images))
            
            with col2:
                if 'clustering' in stats:
                    st.metric("Clusters", stats['clustering'].get('num_clusters', 0))
                else:
                    st.metric("Clusters", "N/A")
            
            with col3:
                blur_removed = 0
                if 'blur_filtering' in stats:
                    blur_removed += stats['blur_filtering'].get('duplicates_removed', 0)
                if 'graph_duplicates' in stats:
                    blur_removed += stats['graph_duplicates'].get('duplicates_marked', 0)
                st.metric("Duplicates Removed", blur_removed)
            
            with col4:
                images_kept = len(images) - blur_removed
                st.metric("Images Kept", images_kept)
            
            st.markdown("---")
            
            # Detailed results
            if 'clustering' in stats:
                with st.expander("🗺️ Clustering Details", expanded=True):
                    clusters = db.get_all_clusters()
                    
                    if clusters:
                        # Create cluster data
                        cluster_data = []
                        for cluster in clusters:
                            cluster_data.append({
                                'Cluster ID': cluster.id,
                                'Name': cluster.name,
                                'Images': cluster.image_count,
                                'Start Time': cluster.start_time,
                                'End Time': cluster.end_time,
                                'Latitude': cluster.center_lat,
                                'Longitude': cluster.center_lon,
                            })
                        
                        df_clusters = pd.DataFrame(cluster_data)
                        st.dataframe(df_clusters, use_container_width=True)
                        
                        # Map visualization
                        if any(c.center_lat for c in clusters):
                            st.subheader("📍 Cluster Map")
                            map_data = df_clusters[df_clusters['Latitude'].notna()][['Latitude', 'Longitude', 'Name', 'Images']]
                            if not map_data.empty:
                                fig = px.scatter_mapbox(
                                    map_data,
                                    lat='Latitude',
                                    lon='Longitude',
                                    hover_name='Name',
                                    hover_data=['Images'],
                                    size='Images',
                                    color='Images',
                                    color_continuous_scale='Teal',
                                    zoom=3,
                                    height=400,
                                )
                                fig.update_layout(
                                    mapbox_style="open-street-map",
                                    margin={"r":0,"t":0,"l":0,"b":0}
                                )
                                st.plotly_chart(fig, use_container_width=True)
            
            if 'graph_duplicates' in stats:
                with st.expander("🕸️ Graph Duplicate Detection", expanded=True):
                    gs = stats['graph_duplicates']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Graph Nodes", gs.get('graph_nodes', 0))
                    with col2:
                        st.metric("Graph Edges", gs.get('graph_edges', 0))
                    with col3:
                        st.metric("Duplicate Groups", gs.get('duplicate_groups', 0))
    
    with tab3:
        st.header("Image Gallery")
        
        if not st.session_state.processed:
            st.info("👈 Upload and process images first!")
        else:
            # Always load fresh images from database to ensure cluster_ids are current
            db = st.session_state.db
            images = db.get_all_images()
            
            if not images:
                st.warning("No images found in database. Please process images first.")
                st.stop()
            
            # Filter options
            view_mode = st.radio(
                "View:",
                ["All Images", "Kept Images Only", "Duplicates Only", "By Cluster"],
                horizontal=True
            )
            
            if view_mode == "By Cluster":
                # Get all cluster IDs that actually have images
                cluster_ids_with_images = set([img.cluster_id for img in images if img.cluster_id is not None])
                
                # Get clusters from database and filter to only those with images
                all_clusters = db.get_all_clusters()
                clusters = [c for c in all_clusters if c.id in cluster_ids_with_images]
                
                if clusters:
                    cluster_names = [f"{c.id}: {c.name}" for c in clusters]
                    selected_cluster = st.selectbox("Select Cluster", cluster_names)
                    cluster_id = int(selected_cluster.split(':')[0])
                    
                    # Get images in cluster
                    display_images = [img for img in images if img.cluster_id == cluster_id]
                else:
                    st.warning("No clusters with images found")
                    display_images = []
            elif view_mode == "Kept Images Only":
                display_images = [img for img in images if not img.is_duplicate]
            elif view_mode == "Duplicates Only":
                display_images = [img for img in images if img.is_duplicate]
            else:
                display_images = images
            
            # Display images in grid
            if display_images:
                st.write(f"Showing {len(display_images)} images")
                
                cols_per_row = 4
                for i in range(0, len(display_images), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(display_images):
                            img_model = display_images[i + j]
                            with col:
                                try:
                                    pil_img = Image.open(img_model.filename)
                                    st.image(pil_img, use_container_width=True)
                                    
                                    # Image info
                                    status = "✅ Kept" if not img_model.is_duplicate else "❌ Duplicate"
                                    st.caption(f"{Path(img_model.filename).name}")
                                    st.caption(f"{status} | Blur: {img_model.blur_score:.2f}")
                                    
                                    pil_img.close()
                                except Exception as e:
                                    st.error(f"Error loading image: {e}")
            else:
                st.info("No images to display")

if __name__ == "__main__":
    main()
