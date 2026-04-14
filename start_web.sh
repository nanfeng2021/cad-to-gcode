#!/bin/bash
# CAD to G-code Platform - Web UI 快速启动脚本

set -e

PROJECT_DIR="/mnt/g/projects/cad-to-gcode"
VENV_DIR="$PROJECT_DIR/venv"

echo "🔧 CAD to G-code Platform - Web UI 启动器"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ 虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 进入项目目录
cd "$PROJECT_DIR"

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    echo "⚠️  配置文件不存在，创建默认配置..."
    mkdir -p config
    cat > config/config.yaml << 'EOF'
project:
  name: "CAD to G-code Platform"
  version: "0.2.0"

model:
  provider: "anthropic"
  model_name: "claude-sonnet-4"

terminal:
  default_shell: "bash"

database:
  path: "/mnt/g/projects/cad-to-gcode/data/programs.db"

web:
  host: "0.0.0.0"
  port: 8000
  static_dir: "src/web/static"

gcode:
  output_dir: "/mnt/g/projects/cad-to-gcode/output"
  default_material: "45#钢"
  default_system: "FANUC"
EOF
fi

# 创建必要目录
mkdir -p data output tests/test_dxf_files

# 检查端口占用
PORT=8000
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  端口 $PORT 已被占用"
    echo "   如果这是之前的实例，可以直接使用"
    echo ""
    echo "🌐 Web UI 已在运行："
    echo "   http://localhost:$PORT/web"
    echo ""
    echo "📚 API 文档："
    echo "   http://localhost:$PORT/docs"
    exit 0
fi

# 启动服务器
echo "🚀 启动 Web 服务器..."
echo ""
echo "🌐 Web UI 地址："
echo "   http://localhost:$PORT/web"
echo ""
echo "📚 API 文档："
echo "   http://localhost:$PORT/docs"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

python -m uvicorn src.web.api:app --reload --host 0.0.0.0 --port $PORT
