#!/bin/bash
# CAD to G-code Platform - 生产部署脚本
# 用途：构建前端、安装依赖、启动服务

set -e

echo "🚀 CAD to G-code Platform - 生产部署"
echo "======================================"

PROJECT_DIR="/mnt/g/projects/cad-to-gcode"
cd "$PROJECT_DIR"

# 步骤 1: 检查 Python 环境
echo ""
echo "📦 步骤 1: 检查 Python 环境..."
if [ ! -d "venv" ]; then
    echo "⚠️  虚拟环境不存在，正在创建..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ Python 环境就绪"

# 步骤 2: 安装前端依赖 (可选)
echo ""
echo "📦 步骤 2: 前端部署..."
if [ -d "src/web/vue-app/node_modules" ]; then
    echo "✓ Node modules 已安装"
else
    echo "⚠️  Node modules 不存在"
    echo "   运行以下命令手动安装:"
    echo "   cd src/web/vue-app && npm install"
fi

# 步骤 3: 构建前端 (如果 node_modules 存在)
if [ -d "src/web/vue-app/node_modules" ]; then
    echo "🔨 构建前端..."
    cd src/web/vue-app
    npm run build
    cd ../..
    echo "✓ 前端构建完成"
else
    echo "⚠️  跳过前端构建 (node_modules 不存在)"
fi

# 步骤 4: 创建静态文件目录
echo ""
echo "📁 步骤 4: 准备静态文件..."
mkdir -p src/web/static

# 如果前端构建成功，复制文件
if [ -d "src/web/vue-app/dist" ]; then
    cp -r src/web/vue-app/dist/* src/web/static/
    echo "✓ 静态文件已复制到 src/web/static/"
else
    # 创建简单的测试页面
    cat > src/web/static/index.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAD to G-code Platform</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .status {
            background: #f0fdf4;
            border-left: 4px solid #22c55e;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .feature {
            background: #f8fafc;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 3px solid #3b82f6;
        }
        .api-link {
            display: inline-block;
            background: #3b82f6;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            margin: 10px 5px;
        }
        .api-link:hover {
            background: #2563eb;
        }
        code {
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 CAD to G-code Platform</h1>
        <p class="subtitle">智能 CAD 到 G 代码转换系统 v0.4.0</p>
        
        <div class="status">
            <strong>✅ 后端服务运行正常</strong><br>
            FastAPI 已成功启动，API 文档可用
        </div>
        
        <h3>🚀 核心功能</h3>
        <div class="feature">
            <strong>✨ Web UI 界面</strong><br>
            Vue 3 + TailwindCSS 现代化前端
        </div>
        <div class="feature">
            <strong>🧠 智能特征识别</strong><br>
            规则引擎 + 机器学习混合系统
        </div>
        <div class="feature">
            <strong>📐 STEP/IGES 支持</strong><br>
            工业标准 CAD 格式解析
        </div>
        <div class="feature">
            <strong>🎬 刀路轨迹仿真</strong><br>
            2D 可视化 + 碰撞检测
        </div>
        
        <h3>📚 API 文档</h3>
        <a href="/docs" class="api-link">📖 Swagger UI</a>
        <a href="/redoc" class="api-link">📄 ReDoc</a>
        <a href="/health" class="api-link">💚 Health Check</a>
        
        <h3>🔧 快速测试</h3>
        <pre style="background: #f1f5f9; padding: 15px; border-radius: 5px; overflow-x: auto;"><code>curl http://localhost:8000/health
curl http://localhost:8000/materials
curl -X POST http://localhost:8000/gcode/generate \
  -H "Content-Type: application/json" \
  -d '{"start_diameter":50,"end_diameter":40,"length":100}'</code></pre>
        
        <p style="text-align: center; color: #999; margin-top: 30px;">
            前端构建中... 请运行 <code>cd src/web/vue-app && npm install && npm run build</code>
        </p>
    </div>
</body>
</html>
EOF
    echo "✓ 创建临时测试页面"
fi

# 步骤 5: 启动服务
echo ""
echo "🚀 步骤 5: 启动服务..."
echo ""
echo "======================================"
echo "✅ 部署完成！"
echo "======================================"
echo ""
echo "📍 访问地址:"
echo "   - 主页面：http://localhost:8000/"
echo "   - API 文档：http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo ""
echo "🔧 启动命令:"
echo "   uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "或后台运行:"
echo "   nohup uvicorn src.web.api:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &"
echo ""

# 自动启动 (询问用户)
read -p "是否现在启动服务？[y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 启动 FastAPI 服务..."
    uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
fi
