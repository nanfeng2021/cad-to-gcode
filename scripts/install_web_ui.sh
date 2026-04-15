#!/bin/bash
# Web UI 安装和构建脚本

set -e

PROJECT_ROOT="/mnt/g/projects/cad-to-gcode"
VUE_APP="$PROJECT_ROOT/src/web/vue-app"

echo "======================================================================"
echo "           CAD to G-code Platform - Web UI Installation"
echo "======================================================================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js (推荐 v18+)"
    echo "   Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"
    echo "   Windows/Mac: 下载安装 https://nodejs.org/"
    exit 1
fi

echo "✓ Node.js 版本：$(node --version)"
echo "✓ npm 版本：$(npm --version)"
echo ""

# 进入 Vue 应用目录
cd "$VUE_APP"

# 安装依赖
echo "📦 安装前端依赖..."
echo ""
npm install

echo ""
echo "✅ 依赖安装完成！"
echo ""
echo "======================================================================"
echo "                           Next Steps"
echo "======================================================================"
echo ""
echo "1. 启动后端 API (终端 1):"
echo "   cd $PROJECT_ROOT"
echo "   source venv/bin/activate"
echo "   python src/web/api.py"
echo ""
echo "2. 启动前端开发服务器 (终端 2):"
echo "   cd $VUE_APP"
echo "   npm run dev"
echo ""
echo "3. 访问应用：http://localhost:3000"
echo ""
echo "4. 生产构建:"
echo "   cd $VUE_APP && npm run build"
echo ""
echo "======================================================================"
