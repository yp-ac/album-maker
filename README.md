# 📸 Smart Album Maker

An intelligent photo organization system with a **complete production-ready DevOps pipeline** for Azure cloud deployment.

## ✨ Features

### 🗺️ **GPS & Time-Based Clustering**
- Automatically groups photos taken at similar locations and times
- Uses hierarchical divide-and-conquer algorithm with Haversine distance
- Configurable distance and time thresholds

### 🎯 **Blur Detection & Filtering**
- Detects image sharpness using Laplacian variance
- Greedy algorithm to remove blurred duplicate images
- Keeps only the sharpest version of similar photos

### 🕸️ **Graph-Based Duplicate Detection**
- Uses perceptual hashing for near-duplicate detection
- NetworkX connected components for transitive duplicate groups
- Handles cropped, rotated, and slightly edited versions

### 🚀 **Production DevOps Pipeline**
- **CI/CD**: Automated testing and deployment with GitHub Actions
- **Containerization**: Multi-stage Docker builds optimized for production
- **Infrastructure as Code**: Azure Bicep templates for reproducible deployments
- **Multi-Environment**: Separate dev, staging, and production environments
- **Monitoring**: Application Insights integration with custom metrics
- **Security**: HTTPS-only, Managed Identity, TLS 1.2, RBAC

## 🚀 Quick Start

### Option 1: Local Development (Python)

```bash
# Clone the repository
git clone <your-repo-url>
cd album-maker

# Install dependencies with uv
uv sync --group dev

# Run tests
uv run pytest

# Start the app
streamlit run app.py
```

### Option 2: Docker (Recommended)

```bash
# Using Docker Compose
docker-compose up --build

# Or using Docker directly
docker build -t album-maker:latest .
docker run -p 8501:8501 -v $(pwd)/data:/app/data album-maker:latest
```

### Option 3: Deploy to Azure

**📖 See [SETUP_CREDENTIALS.md](SETUP_CREDENTIALS.md) for the complete step-by-step guide.**

Quick overview:
```bash
# 1. Login and create container registry
az login
az acr create --resource-group college --name cracalbummaker --sku Basic --admin-enabled true

# 2. Get credentials and add to GitHub secrets
az ad sp create-for-rbac --name "github-album-maker-deploy" --role contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/college --json-auth

# 3. Deploy infrastructure
az deployment group create \
  --resource-group college \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters.json

# 4. Push to trigger automatic deployment
git push origin main
```

The app will be available at: `https://app-album-maker.azurewebsites.net`

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
├── .github/workflows/
│   ├── ci.yml                      # CI pipeline (testing)
│   └── cd.yml                      # CD pipeline (deployment to Azure)
├── infrastructure/
│   ├── main.bicep                  # Azure infrastructure template
│   ├── parameters.*.json           # Environment configs (dev/staging/prod)
│   └── SETUP.md                    # Azure deployment guide
├── src/
│   ├── clustering.py               # GPS/Time clustering (Divide & Conquer)
│   ├── duplicate_detection.py      # Blur filtering (Greedy)
│   ├── graph_duplicates.py         # Graph duplicate detection
│   ├── app_insights.py             # Application Insights monitoring
│   ├── image_processing.py         # Image analysis utilities
│   ├── database.py                 # SQLite database operations
│   ├── models.py                   # Data models
│   └── error_handling.py           # Error handling utilities
├── tests/
│   ├── test_clustering.py          # 23 tests for clustering
│   ├── test_duplicate_detection.py # 6 tests for duplicates
│   └── test_graph_duplicates.py    # 13 tests for graph algorithms
├── app.py                          # Streamlit web application
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Local development setup
├── pytest.ini                      # Test configuration
├── pyproject.toml                  # Dependencies & config
├── QUICKSTART.md                   # Quick reference guide
├── DOCKER.md                       # Docker documentation
├── DEVOPS.md                       # DevOps architecture
└── PROJECT_SUMMARY.md              # Complete implementation summary
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

### Application
- **Frontend**: Streamlit (with custom teal theme)
- **Backend**: Python 3.13+
- **Image Processing**: Pillow, OpenCV, ImageHash
- **Graph Analysis**: NetworkX
- **Data Visualization**: Plotly, Pandas
- **Database**: SQLite3

### DevOps & Cloud
- **CI/CD**: GitHub Actions
- **Containerization**: Docker, Docker Compose
- **Cloud Platform**: Microsoft Azure
  - App Service (Linux containers)
  - Container Registry (ACR)
  - Application Insights
  - Storage Account
- **IaC**: Azure Bicep
- **Monitoring**: OpenCensus, Application Insights
- **Testing**: pytest (42 tests, >80% coverage)

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

### Application Issues

#### Images not clustering?
- Check if images have GPS metadata (EXIF data)
- Try increasing distance/time thresholds
- Some images may not have location data

#### Too many duplicates detected?
- Increase similarity threshold (make it more strict)
- Adjust blur threshold to be less aggressive

#### App not starting?
- Make sure all dependencies are installed: `uv sync`
- Check Python version: `python --version` (should be 3.13+)
- Try: `streamlit run app.py`

### Docker Issues

#### Container fails to start?
```bash
# Check logs
docker-compose logs -f

# Test image locally
docker run -it album-maker:latest /bin/bash
```

#### Port already in use?
```bash
# Use different port
docker run -p 8502:8501 album-maker:latest
```

### Azure Deployment Issues

See **[infrastructure/SETUP.md](infrastructure/SETUP.md)** for detailed troubleshooting:
- Service principal authentication
- Container registry credentials  
- Health check failures
- Application Insights configuration

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference for common tasks
- **[DOCKER.md](DOCKER.md)** - Docker usage and configuration
- **[DEVOPS.md](DEVOPS.md)** - Complete DevOps architecture
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Implementation summary
- **[infrastructure/SETUP.md](infrastructure/SETUP.md)** - Azure deployment guide

## 🎓 Learning Objectives

This project demonstrates:

### Algorithms & Data Structures
- ✅ Divide & Conquer (hierarchical clustering)
- ✅ Greedy Algorithms (blur filtering)
- ✅ Graph Algorithms (connected components)
- ✅ Complexity Analysis (O(n²), O(n log n), O(V+E))

### DevOps & Cloud
- ✅ CI/CD Pipeline design
- ✅ Infrastructure as Code
- ✅ Container orchestration
- ✅ Cloud deployment
- ✅ Monitoring & observability
- ✅ Multi-environment management
- ✅ Security best practices

## 📜 License

MIT License - feel free to use for your projects!

## 🙏 Acknowledgments

Built using:
- [Streamlit](https://streamlit.io/) - Web framework
- [NetworkX](https://networkx.org/) - Graph algorithms
- [ImageHash](https://github.com/JohannesBuchner/imagehash) - Perceptual hashing
- [Pillow](https://python-pillow.org/) - Image processing

## 🚧 Future Enhancements

### Application Features
- [ ] Cloud storage integration (Google Photos, Dropbox)
- [ ] Machine learning-based quality assessment
- [ ] Face recognition for person-based clustering
- [ ] Export to different album formats

### DevOps Improvements
- [ ] Auto-scaling configuration
- [ ] Blue-green deployments
- [ ] Canary releases
- [ ] Custom domain with SSL
- [ ] CDN for static assets
- [ ] Automated backup strategy
- [ ] Disaster recovery plan

---

**Made with ❤️ using advanced algorithms, a teal theme, and production-ready DevOps! 🎨☁️**
