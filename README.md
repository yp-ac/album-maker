# 📸 Smart Album Maker

An intelligent photo organization system that uses advanced algorithms to automatically cluster, filter, and organize your images.

## ✨ Features

### 🗺️ **GPS & Time-Based Clustering**
- Automatically groups photos taken at similar locations and times
- Uses hierarchical clustering with Haversine distance calculation
- Configurable distance and time thresholds

### 🎯 **Blur Detection & Filtering**
- Detects image sharpness using Laplacian variance
- Automatically removes blurred duplicate images
- Keeps only the sharpest version of similar photos

### 🕸️ **Graph-Based Duplicate Detection**
- Uses perceptual hashing for near-duplicate detection
- Finds transitive duplicates (if A≈B and B≈C, groups all three)
- Handles cropped, rotated, and slightly edited versions

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- `uv` package manager (recommended) or `pip`

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd album-maker

# Install dependencies
uv sync

# Or with pip
pip install -r requirements.txt
```

### Running the App

```bash
# Start the Streamlit web interface
uv run streamlit run app.py

# Or with python directly
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 🎨 Usage

1. **Upload Photos**: Drag and drop or select multiple image files (JPG, PNG)

2. **Configure Settings** (in sidebar):
   - **Distance threshold**: How close photos must be to cluster (km)
   - **Time threshold**: How close in time photos must be (hours)
   - **Blur threshold**: Minimum quality to keep images
   - **Similarity threshold**: How similar photos must be for duplicate detection

3. **Process**: Click "Process Images" to run all algorithms

4. **View Results**:
   - See summary statistics and metrics
   - Explore clusters on an interactive map
   - Browse kept images and duplicates
   - View images by cluster

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run specific test file
uv run python -m pytest tests/test_clustering.py -v

# Run with coverage
uv run python -m pytest tests/ --cov=src
```

### Manual Testing Scripts

```bash
# Test GPS/Time clustering
uv run python manual_test_clustering.py

# Test blur detection
uv run python manual_test_blur_filtering.py

# Test graph-based duplicates
uv run python manual_test_graph_duplicates.py
```

## 📁 Project Structure

```
album-maker/
├── app.py                          # Streamlit web application
├── src/
│   ├── clustering.py               # GPS/Time clustering algorithms
│   ├── duplicate_detection.py      # Blur filtering & duplicate detection
│   ├── graph_duplicates.py         # Graph-based duplicate detection
│   ├── image_processing.py         # Image analysis utilities
│   ├── database.py                 # SQLite database operations
│   ├── models.py                   # Data models
│   └── error_handling.py           # Error handling utilities
├── tests/
│   ├── test_clustering.py          # Clustering tests (23 tests)
│   ├── test_duplicate_detection.py # Duplicate detection tests (6 tests)
│   └── test_graph_duplicates.py    # Graph algorithm tests (13 tests)
├── specs/                          # Feature specifications
└── pyproject.toml                  # Project configuration
```

## 🔬 Algorithms Used

### 1. Divide & Conquer
- **Hierarchical Clustering**: Recursively groups images by GPS distance and time proximity
- **Complexity**: O(n²) for distance calculation, O(n log n) for clustering

### 2. Greedy Selection
- **Blur Filtering**: Selects sharpest image from duplicate groups
- **Complexity**: O(n) for selection within groups

### 3. Graph Algorithms
- **Connected Components**: Uses NetworkX to find duplicate groups
- **Perceptual Hashing**: ImageHash library for similarity detection
- **Complexity**: O(V + E) for connected components, O(n²) for edge construction

## 📊 Test Coverage

- **42 automated tests** across all modules
- **100% passing** test rate
- Coverage for:
  - GPS distance calculations (Haversine formula)
  - Time proximity detection
  - Hierarchical clustering
  - Blur score calculation (Laplacian variance)
  - Greedy duplicate selection
  - Graph construction and analysis
  - Database operations

## 🎨 Technology Stack

- **Frontend**: Streamlit (with custom teal theme)
- **Backend**: Python 3.13+
- **Image Processing**: Pillow, OpenCV, ImageHash
- **Graph Analysis**: NetworkX
- **Data Visualization**: Plotly, Pandas
- **Database**: SQLite3
- **Testing**: pytest

## 📝 Configuration Options

### Clustering Parameters
- `distance_threshold`: 0.1 - 10.0 km (default: 1.0)
- `time_threshold`: 0.5 - 24.0 hours (default: 3.0)

### Quality Filtering
- `blur_threshold`: 0.0 - 1.0 (default: 0.3)
  - Higher = keep more images
  - Lower = stricter quality filter

### Duplicate Detection
- `similarity_threshold`: 1 - 20 bits (default: 10)
  - Lower = stricter matching (exact duplicates)
  - Higher = more lenient (near-duplicates)

## 🐛 Troubleshooting

### Images not clustering?
- Check if images have GPS metadata (EXIF data)
- Try increasing distance/time thresholds
- Some images may not have location data

### Too many duplicates detected?
- Increase similarity threshold (make it more strict)
- Adjust blur threshold to be less aggressive

### App not starting?
- Make sure all dependencies are installed: `uv sync`
- Check Python version: `python --version` (should be 3.13+)
- Try: `uv run streamlit run app.py`

## 📜 License

MIT License - feel free to use for your projects!

## 🙏 Acknowledgments

Built using:
- [Streamlit](https://streamlit.io/) - Web framework
- [NetworkX](https://networkx.org/) - Graph algorithms
- [ImageHash](https://github.com/JohannesBuchner/imagehash) - Perceptual hashing
- [Pillow](https://python-pillow.org/) - Image processing

## 🚧 Future Enhancements

- [ ] Cloud storage integration (Google Photos, Dropbox)
- [ ] Batch processing for large collections
- [ ] Machine learning-based quality assessment
- [ ] Face recognition for person-based clustering
- [ ] Export to different album formats
- [ ] Progressive web app (PWA) support

---

Made with ❤️ using advanced algorithms and a teal theme! 🎨
