#!/bin/bash
# CAD to G-code Platform - Quick Start Script
# Usage: ./start.sh [dev|prod|test]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     CAD to G-code Platform - Quick Start              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Docker availability
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_status "Docker is available"
}

# Check Docker Compose
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        print_error "Docker Compose is not installed."
        exit 1
    fi
    
    print_status "Docker Compose is available ($COMPOSE_CMD)"
}

# Create necessary directories
setup_directories() {
    print_status "Setting up directories..."
    
    mkdir -p logs output data/samples .cache/models
    touch data/samples/.gitkeep
    
    print_status "Directories created"
}

# Start development mode
start_dev() {
    echo -e "${YELLOW}Starting in DEVELOPMENT mode...${NC}"
    echo ""
    
    check_docker
    check_docker_compose
    setup_directories
    
    # Build and start
    $COMPOSE_CMD up --build -d
    
    echo ""
    print_status "Services started!"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  📡 API Documentation: http://localhost:8000/docs"
    echo "  📊 Health Check:      http://localhost:8000/health"
    echo "  📁 Materials List:    http://localhost:8000/materials"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "View logs: docker-compose logs -f app"
    echo "Stop:      docker-compose down"
    echo "Shell:     docker-compose exec app bash"
    echo ""
}

# Start production mode
start_prod() {
    echo -e "${YELLOW}Starting in PRODUCTION mode...${NC}"
    echo ""
    
    check_docker
    check_docker_compose
    setup_directories
    
    # Build production image
    docker build -t cad-to-gcode:latest .
    
    # Run container
    docker run -d \
        -p 8000:8000 \
        -v $(pwd)/output:/app/output \
        -v $(pwd)/logs:/app/logs \
        --name cad2gcode-prod \
        --restart unless-stopped \
        cad-to-gcode:latest \
        uvicorn src.web.api:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 2
    
    echo ""
    print_status "Production server started!"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  📡 API: http://localhost:8000"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "View logs: docker logs -f cad2gcode-prod"
    echo "Stop:      docker stop cad2gcode-prod"
    echo "Restart:   docker restart cad2gcode-prod"
    echo ""
}

# Run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"
    echo ""
    
    check_docker
    check_docker_compose
    
    # Run tests in container
    $COMPOSE_CMD run --rm cli python -m pytest tests/ -v --tb=short
    
    echo ""
    print_status "Tests completed!"
}

# Local development (no Docker)
start_local() {
    echo -e "${YELLOW}Starting LOCAL development server...${NC}"
    echo ""
    
    # Check Python
    if ! command -v python &> /dev/null; then
        print_error "Python is not installed."
        exit 1
    fi
    
    # Check virtual environment
    if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
        print_warning "Virtual environment not found. Creating..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -q -e ".[dev]"
    
    setup_directories
    
    echo ""
    print_status "Starting server..."
    echo ""
    
    uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
}

# Show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev       Start development server with Docker Compose (default)"
    echo "  prod      Start production server with Docker"
    echo "  local     Start local development server (no Docker)"
    echo "  test      Run test suite"
    echo "  stop      Stop all running containers"
    echo "  logs      View logs"
    echo "  shell     Open shell in running container"
    echo "  clean     Clean up containers and volumes"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev        # Start development mode"
    echo "  $0 prod       # Start production mode"
    echo "  $0 test       # Run tests"
    echo "  $0 logs       # View application logs"
    echo ""
}

# Main command handler
case "${1:-dev}" in
    dev|development)
        start_dev
        ;;
    prod|production)
        start_prod
        ;;
    local)
        start_local
        ;;
    test|tests)
        run_tests
        ;;
    stop)
        check_docker_compose
        $COMPOSE_CMD down
        print_status "Services stopped"
        ;;
    logs)
        check_docker_compose
        $COMPOSE_CMD logs -f app
        ;;
    shell|bash)
        check_docker_compose
        $COMPOSE_CMD exec app bash
        ;;
    clean)
        check_docker_compose
        $COMPOSE_CMD down -v
        docker rm -f cad2gcode-prod 2>/dev/null || true
        print_status "Cleanup complete"
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
