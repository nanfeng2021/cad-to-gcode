# Web UI 开发指南

## 📋 目录

- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [开发模式](#开发模式)
- [构建部署](#构建部署)
- [功能特性](#功能特性)
- [API 集成](#api-集成)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /mnt/g/projects/cad-to-gcode/src/web/vue-app

# 使用 npm
npm install

# 或使用 yarn
yarn install

# 或使用 pnpm
pnpm install
```

### 2. 启动开发服务器

```bash
# 终端 1: 启动后端 API (端口 8000)
cd /mnt/g/projects/cad-to-gcode
source venv/bin/activate
python src/web/api.py

# 终端 2: 启动前端开发服务器 (端口 3000)
cd /mnt/g/projects/cad-to-gcode/src/web/vue-app
npm run dev
```

访问 http://localhost:3000 查看应用

---

## 📁 项目结构

```
vue-app/
├── index.html                 # HTML 入口
├── package.json              # 依赖配置
├── vite.config.js            # Vite 配置
├── tailwind.config.js        # TailwindCSS 配置
├── postcss.config.js         # PostCSS 配置
└── src/
    ├── main.js               # Vue 应用入口
    ├── App.vue               # 主组件
    ├── assets/
    │   └── main.css          # 全局样式
    ├── router/
    │   └── index.js          # 路由配置
    ├── store/                # Pinia 状态管理 (可选)
    └── views/
        ├── HomeView.vue      # 首页
        ├── UploadView.vue    # 上传页面
        ├── ProgramsView.vue  # 程序管理
        └── SettingsView.vue  # 设置页面
```

---

## 💻 开发模式

### 热重载开发

```bash
npm run dev
```

- 自动热重载 (HMR)
- 源码映射
- 错误覆盖层显示

### 代码规范

推荐使用 ESLint + Prettier:

```bash
npm install -D eslint prettier eslint-plugin-vue
```

---

## 🏗️ 构建部署

### 生产构建

```bash
npm run build
```

输出目录：`src/web/static/`

构建后的文件会自动复制到 FastAPI 的静态文件目录，可直接通过 `http://localhost:8000` 访问。

### 预览构建结果

```bash
npm run preview
```

---

## ✨ 功能特性

### 1. DXF 文件上传

- ✅ 拖拽上传
- ✅ 批量选择多个文件
- ✅ 文件大小限制检查
- ✅ 实时进度显示
- ✅ 错误处理和重试

### 2. 加工参数配置

- ✅ 材料选择 (5 种)
- ✅ 数控系统选择 (5 种)
- ✅ 保存选项配置
- ✅ 默认参数记忆

### 3. DXF 几何预览

- ✅ Canvas 2D 渲染
- ✅ 自动缩放和平移
- ✅ 坐标轴显示
- ✅ 实体绘制 (LINE, CIRCLE, ARC)
- ✅ 特征识别结果展示

### 4. G 代码查看器

- ✅ 语法高亮 (零依赖)
- ✅ 行号显示
- ✅ 复制功能
- ✅ 下载 NC 文件
- ✅ 滚动同步

### 5. 程序管理

- ✅ 列表展示
- ✅ 搜索过滤
- ✅ 材料/系统筛选
- ✅ 查看详情
- ✅ 删除确认
- ✅ 批量操作

### 6. 响应式设计

- ✅ 移动端适配
- ✅ 平板优化
- ✅ 桌面端增强
- ✅ 深色模式支持 (待实现)

---

## 🔌 API 集成

### 代理配置

Vite 配置了 API 代理 (`vite.config.js`):

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```

### 主要 API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/gcode/upload-dxf` | POST | 上传 DXF 并生成 |
| `/programs` | GET | 获取程序列表 |
| `/programs/{id}` | GET | 获取单个程序 |
| `/programs/{id}` | DELETE | 删除程序 |
| `/materials` | GET | 材料列表 |
| `/cutting-params` | POST | 切削参数查询 |

### Axios 封装 (可选)

创建 `src/utils/api.js`:

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器
api.interceptors.request.use(config => {
  // 添加 token 等
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default api
```

---

## 🎨 自定义样式

### TailwindCSS 扩展

编辑 `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: '#3B82F6',
      secondary: '#10B981',
    },
    animation: {
      'spin-slow': 'spin 3s linear infinite',
    },
  },
}
```

### 全局 CSS

编辑 `src/assets/main.css`:

```css
@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-primary text-white rounded hover:bg-blue-600;
  }
  
  .card {
    @apply bg-white rounded-lg shadow p-6;
  }
}
```

---

## 🐛 常见问题

### Q: 开发服务器无法连接后端？

A: 确保后端 API 在运行：
```bash
python src/web/api.py
```

### Q: 构建后页面空白？

A: 检查 `vite.config.js` 中的 `outDir` 配置，确保指向正确的静态文件目录。

### Q: Canvas 预览不显示？

A: 检查 DXF 解析返回的 entities 格式，确保包含正确的坐标数据。

### Q: 跨域错误？

A: FastAPI 已配置 CORS 中间件，允许所有来源。生产环境应限制具体域名。

---

## 📈 性能优化建议

1. **代码分割**: 使用路由懒加载
   ```javascript
   const UploadView = () => import('@/views/UploadView.vue')
   ```

2. **图片优化**: 使用 WebP 格式，压缩 SVG

3. **缓存策略**: 利用浏览器缓存静态资源

4. **Gzip 压缩**: 启用 Nginx/Apache 的 gzip

5. **CDN 加速**: 将静态资源部署到 CDN

---

## 🔜 待实现功能

- [ ] 深色模式切换
- [ ] 多语言支持 (i18n)
- [ ] 用户认证系统
- [ ] 权限管理
- [ ] 刀路仿真可视化
- [ ] STEP/IGES 格式支持
- [ ] 移动端手势支持
- [ ] 离线 PWA 支持

---

## 📞 技术支持

遇到问题？

1. 查看控制台错误信息
2. 检查网络请求 (DevTools Network 面板)
3. 查阅 FastAPI 日志
4. 参考 Hermes Agent 文档

---

**最后更新**: 2026-04-15  
**版本**: v0.2.0  
**维护者**: Nanfeng
