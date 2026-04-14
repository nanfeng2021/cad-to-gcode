# CAD to G-code Platform

AI-powered CAD to G-code generation platform for 2-axis CNC lathes.

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 Overview

This platform automatically converts CAD files (STEP, IGES, DXF, DWG) into optimized G-code programs for CNC lathe machining. It uses AI-based feature recognition and rule-based process planning to generate efficient machining strategies.

### Key Features

- **CAD File Parsing** - Support for STEP, IGES, DXF, DWG formats
- **AI Feature Recognition** - Automatic detection of machining features (cylinders, grooves, threads)
- **Process Planning** - Intelligent operation sequencing (roughing → finishing → grooving → threading)
- **Cutting Parameter Database** - Material-specific cutting parameters from industry experience
- **Multi-System Support** - Generate G-code for FANUC, Siemens, Mitsubishi, GSK, HNC controls
- **Web Interface** - RESTful API with automatic documentation
- **Docker Support** - Easy deployment with Docker Compose

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  CAD File   │ ──▶ │  AI Feature  │ ──▶ │ Process Planning │
│ (STEP/DXF)  │     │  Recognition │     │  & Tool Selection│
└─────────────┘     └──────────────┘     └─────────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  G-code     │ ◀── │  Simulation  │ ◀── │ Cutting Params  │
│  Output     │     │  & Verify    │     │  Calculation    │
└─────────────┘     └──────────────┘     └─────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/nanfeng2021/cad-to-gcode.git
cd cad-to-gcode

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Access the API
open http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start the API server
uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000

# Use the CLI
python -m src.cli materials
python -m src.cli tools
```

### Option 3: Direct Docker

```bash
# Build the image
docker build -t cad-to-gcode:latest .

# Run the container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/data/samples:/app/data/samples \
  --name cad2gcode \
  cad-to-gcode:latest

# Access the API
curl http://localhost:8000/health
```

## 📖 API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-04-13T23:59:59",
  "config_loaded": true,
  "materials_count": 6
}
```

### List Materials

```bash
curl http://localhost:8000/materials
```

### Get Cutting Parameters

```bash
curl -X POST http://localhost:8000/cutting-params \
  -H "Content-Type: application/json" \
  -d '{
    "material": "45#钢",
    "operation": "粗车"
  }'
```

### Generate G-code (Simple Shaft)

```bash
curl -X POST http://localhost:8000/gcode/generate \
  -H "Content-Type: application/json" \
  -d '{
    "start_diameter": 50,
    "end_diameter": 30,
    "length": 100,
    "material": "45#钢",
    "machine_system": "FANUC"
  }'
```

### Upload CAD File

```bash
curl -X POST http://localhost:8000/gcode/upload-cad \
  -F "file=@part.step" \
  -F "material=45#钢" \
  -F "machine_system=FANUC"
```

### Interactive Documentation

Open your browser and visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🛠️ CLI Commands

```bash
# Show version
python -m src.cli version

# List supported materials
python -m src.cli materials

# List available tools
python -m src.cli tools

# Show configuration
python -m src.cli config show

# Process a CAD file
python -m src.cli process part.step -m "45#钢" -o part.nc

# Run tests
python -m src.cli test
```

## 📁 Project Structure

```
cad-to-gcode/
├── src/                      # Source code
│   ├── __init__.py
│   ├── cli.py                # Command-line interface
│   ├── config_loader.py      # Configuration management
│   ├── core/                 # Core modules
│   │   ├── __init__.py
│   │   └── process_planning.py  # Cutting rules engine
│   ├── ai/                   # AI/ML modules (future)
│   │   └── __init__.py
│   ├── web/                  # Web API
│   │   ├── __init__.py
│   │   └── api.py            # FastAPI application
│   └── cam/                  # CAM modules
│       ├── __init__.py
│       └── gcode_generator.py   # G-code generation
├── config/                   # Configuration files
│   ├── config.yaml           # Main configuration
│   └── cutting_rules.yaml    # Cutting parameter database
├── data/                     # Data files
│   ├── tools/                # Tool definitions
│   ├── materials/            # Material properties
│   └── samples/              # Sample CAD files
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── docs/                     # Documentation
├── output/                   # Generated G-code output
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker image definition
├── pyproject.toml            # Python project configuration
└── README.md                 # This file
```

## ⚙️ Configuration

Edit `config/config.yaml` to customize:

```yaml
project:
  name: cad-to-gcode
  version: 0.1.0
  target_machine: FANUC 2-axis lathe

web:
  host: 0.0.0.0
  port: 8000
  debug: true

gcode:
  default_system: FANUC
  include_comments: true
  safety_checks: true

logging:
  level: INFO
  file: logs/cad2gcode.log
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_process_planning.py -v

# Run tests in Docker
docker-compose run --rm cli test
```

## 🔧 Development

### Setup Development Environment

```bash
# Clone and enter directory
git clone https://github.com/nanfeng2021/cad-to-gcode.git
cd cad-to-gcode

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run linting
ruff check src/
black --check src/
mypy src/
```

### Building Docker Image

```bash
# Build production image
docker build -t cad-to-gcode:latest .

# Build development image
docker build --target development -t cad-to-gcode:dev .

# Push to registry
docker tag cad-to-gcode:latest registry.example.com/cad-to-gcode:latest
docker push registry.example.com/cad-to-gcode:latest
```

## 📊 Supported Materials

| Material | Code | Hardness | Operations |
|----------|------|----------|------------|
| 45#钢 | STEEL_45 | HRC 20-30 | Rough, Finish, Groove, Thread |
| 40Cr | STEEL_40CR | HRC 25-35 | Rough, Finish, Groove, Thread |
| 不锈钢 | STAINLESS | HRC 15-25 | Rough, Finish, Groove |
| 铝合金 | ALUMINUM | HB 60-100 | Rough, Finish, Groove |
| 黄铜 | BRASS | HB 80-150 | Rough, Finish |
| 铸钢 | CAST_STEEL | HRC 18-28 | Rough, Finish |

## 🔐 Security

- File upload validation (type, size)
- Input sanitization
- CORS configuration
- Rate limiting (TODO)
- Authentication (TODO)

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 👥 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Contact

- **Author**: Nanfeng
- **GitHub**: [@nanfeng2021](https://github.com/nanfeng2021)
- **Issues**: [GitHub Issues](https://github.com/nanfeng2021/cad-to-gcode/issues)

## 🙏 Acknowledgments

- Inspired by [Hermes Agent](https://github.com/NousResearch/hermes-agent) engineering patterns
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Docker support for easy deployment
