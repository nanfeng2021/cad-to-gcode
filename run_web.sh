#!/bin/bash
# CAD to G-code Platform - Web Server Launcher

cd /mnt/g/projects/cad-to-gcode

echo "🚀 Starting CAD to G-code Web Server..."
echo "📍 Project: $(pwd)"
echo "🌐 Web UI: http://localhost:8000/web"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""

source venv/bin/activate
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload
