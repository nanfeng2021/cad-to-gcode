# CAD to G-code Platform - 中期增强功能实现报告

## 📋 概述

本报告记录了 CAD to G-code Platform 中期增强功能的实现进度。中期目标包括 4 个主要功能模块，旨在将平台从单用户工具升级为企业级多用户 SaaS 应用。

---

## ✅ 已完成功能

### 1. 👥 用户系统（多用户隔离）

**状态：** ✅ 完成  
**实现时间：** 2026-04-14

#### 功能描述
完整的用户认证和授权系统，支持多用户数据隔离，确保每个用户只能访问自己的程序和数据。

#### 核心特性

**1.1 用户管理**
- ✅ 用户注册（用户名、邮箱、密码）
- ✅ 用户登录（JWT Token 认证）
- ✅ 用户登出（Token 失效）
- ✅ 当前用户信息查询
- ✅ 默认管理员账户（admin/admin123）

**1.2 权限控制**
- ✅ 基于角色的访问控制（RBAC）
  - `admin`：查看所有用户程序，管理用户
  - `user`：仅查看和管理自己的程序
- ✅ JWT Token 验证中间件
- ✅ 会话管理（Token 存储和失效）

**1.3 用户偏好**
- ✅ 默认材料设置
- ✅ 默认 CNC 系统设置
- ✅ 主题偏好（预留）
- ✅ 语言偏好（预留）

**1.4 数据隔离**
- ✅ 程序表 user_id 字段
- ✅ 按用户过滤程序列表
- ✅ 按用户过滤搜索结果
- ✅ 管理员可查看所有数据

#### 技术实现

**数据库 Schema：**
```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- 会话表
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_valid BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 用户偏好表
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    default_material TEXT DEFAULT '45#钢',
    default_machine_system TEXT DEFAULT 'FANUC',
    theme TEXT DEFAULT 'light',
    language TEXT DEFAULT 'zh-CN',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 程序表（已更新）
ALTER TABLE programs ADD COLUMN user_id INTEGER;
CREATE INDEX idx_programs_user_id ON programs(user_id);
```

**安全机制：**
- bcrypt 密码哈希（salt rounds=12）
- JWT Token 认证（24 小时有效期）
- HTTPS 传输加密（生产环境部署时）
- SQL 注入防护（参数化查询）

**API 端点：**

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/auth/register` | POST | ❌ | 用户注册 |
| `/auth/login` | POST | ❌ | 用户登录 |
| `/auth/logout` | POST | ✅ | 用户登出 |
| `/auth/me` | GET | ✅ | 获取当前用户信息 |
| `/users/preferences` | GET | ✅ | 获取用户偏好 |
| `/users/preferences` | POST | ✅ | 更新用户偏好 |
| `/users` | GET | ✅(admin) | 列出所有用户 |
| `/programs` | GET | ✅ | 获取程序列表（用户隔离） |
| `/programs/search` | GET | ✅ | 搜索程序（用户隔离） |
| `/programs` | POST | ✅ | 保存程序（自动关联用户） |

#### 代码文件

**新增文件：**
- `/mnt/g/projects/cad-to-gcode/src/storage/user_management.py` (454 行)
  - `UserDatabase` 类：用户数据库管理
  - `User` 数据类：用户数据结构
  - JWT Token 生成和验证
  - 密码哈希和验证

**修改文件：**
- `/mnt/g/projects/cad-to-gcode/src/web/api.py`
  - 添加用户认证模型
  - 添加认证依赖注入
  - 添加用户 API 端点
  - 更新程序端点支持用户隔离
  
- `/mnt/g/projects/cad-to-gcode/src/storage/gcode_storage.py`
  - `save_program()`: 添加 user_id 参数
  - `list_programs()`: 添加 user_id 过滤
  - `search_programs()`: 添加 user_id 过滤

- `/mnt/g/projects/cad-to-gcode/requirements.txt`
  - 添加 `bcrypt>=4.0.0`
  - 添加 `PyJWT>=2.8.0`

#### 使用示例

**注册新用户：**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"nanfeng","email":"nanfeng@example.com","password":"mypassword123"}'
```

**登录获取 Token：**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**访问受保护的资源：**
```bash
curl http://localhost:8000/programs \
  -H "Authorization: Bearer <your_token>"
```

**更新用户偏好：**
```bash
curl -X POST http://localhost:8000/users/preferences \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"default_material":"铝合金","default_machine_system":"Siemens"}'
```

#### 测试结果

```bash
# ✓ 健康检查
curl http://localhost:8000/health
# 返回：{"status": "healthy", ...}

# ✓ 管理员登录
curl -X POST http://localhost:8000/auth/login \
  -d '{"username":"admin","password":"admin123"}'
# 返回：{"success": true, "token": "...", "user": {...}}

# ✓ 获取当前用户信息
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
# 返回：{"id": 1, "username": "admin", "role": "admin"}

# ✓ 用户隔离测试
# 用户 A 登录后创建程序
# 用户 B 登录后只能看到自己的程序，看不到用户 A 的
```

#### 默认账户

**管理员账户：**
- 用户名：`admin`
- 密码：`admin123`
- 角色：`admin`
- 邮箱：`admin@example.com`

⚠️ **重要：** 首次登录后请立即修改默认密码！

---

## ⏳ 待实现功能

### 2. ✏️ 在线编辑 G 代码

**状态：** ⏳ 计划中

#### 功能规划

**核心功能：**
1. Monaco Editor 集成（VSCode 同款编辑器）
2. G 代码语法高亮（自定义语言定义）
3. 代码自动补全（G/M/T/S/F 代码提示）
4. 实时保存修改
5. 版本历史（可选）
6. 差异对比（修改前后对比）

**技术选型：**
- 编辑器：Monaco Editor（轻量级 CDN 加载）
- 语法定义：自定义 Monarch tokenizer
- 存储：IndexedDB（本地缓存）+ SQLite（持久化）

**API 端点规划：**
```
PUT /programs/{id}/content  # 更新程序内容
GET /programs/{id}/history  # 获取版本历史
```

---

### 3. 🎬 加工路径动画仿真

**状态：** ⏳ 计划中

#### 功能规划

**核心功能：**
1. 2D 刀具路径可视化
2. 加工过程动画播放
3. 速度控制（0.5x, 1x, 2x, 4x）
4. 逐段执行（单步调试）
5. 碰撞检测预警
6. 加工时间估算

**技术方案：**
- 渲染引擎：HTML5 Canvas 或 SVG
- 解析器：G 代码解析（提取坐标和动作）
- 动画：requestAnimationFrame
- 坐标系：笛卡尔坐标（XZ 平面）

**可视化元素：**
- 工件轮廓（灰色）
- 刀具路径（紫色渐变）
- 当前位置标记（红色圆点）
- 坐标轴标注
- 刻度尺

**API 端点规划：**
```
GET /programs/{id}/toolpath  # 获取刀具路径数据
POST /simulation/analyze     # 分析 G 代码并返回路径
```

---

### 4. 📄 导出 PDF/HTML 工艺单

**状态：** ⏳ 计划中

#### 功能规划

**核心功能：**
1. 工艺单模板生成
2. PDF 导出（打印友好）
3. HTML 导出（可交互）
4. 批量导出
5. 自定义模板（企业 Logo）

**工艺单内容：**
- 零件信息（文件名、材料、尺寸）
- 加工工艺（工序列表、切削参数）
- G 代码预览（带行号）
- 刀具路径图（缩略图）
- 二维码（快速访问）

**技术方案：**
- PDF 生成：ReportLab 或 WeasyPrint
- HTML 模板：Jinja2
- 图表：Matplotlib（刀具路径图）

**API 端点规划：**
```
GET /programs/{id}/export/pdf    # 导出 PDF
GET /programs/{id}/export/html   # 导出 HTML
GET /programs/{id}/export/dxf    # 导出 DXF（刀具路径）
```

---

## 📊 项目结构更新

```
cad-to-gcode/
├── src/
│   ├── storage/
│   │   ├── gcode_storage.py      # ✓ 已更新（支持 user_id）
│   │   └── user_management.py    # ✓ 新增（用户管理）
│   └── web/
│       ├── api.py                # ✓ 已更新（认证端点）
│       └── static/
│           └── index.html        # ⏳ 待更新（登录 UI）
├── data/
│   ├── programs.db               # 程序数据库
│   └── users.db                  # ✓ 新增（用户数据库）
├── requirements.txt              # ✓ 已更新（bcrypt, PyJWT）
└── docs/
    └── USER_SYSTEM.md            # ✓ 本文档
```

---

## 🔐 安全建议

### 生产环境部署清单

1. **修改默认密码**
   ```bash
   # 登录后立即修改 admin 密码
   ```

2. **启用 HTTPS**
   - 配置 SSL 证书
   - 强制 HTTPS 重定向
   - HSTS 头设置

3. **Token 安全**
   - 缩短 Token 有效期（建议 4-8 小时）
   - 实现 Refresh Token 机制
   - Token 黑名单（登出时加入）

4. **密码策略**
   - 最小长度 8 位
   - 要求大小写字母 + 数字
   - 密码强度检测

5. **速率限制**
   - 登录接口限流（防暴力破解）
   - API 请求限流（防滥用）

6. **日志审计**
   - 记录所有登录尝试
   - 记录敏感操作（删除、修改）
   - 定期审查日志

---

## 🚀 下一步计划

### Phase 2.1: 在线编辑器（预计 2-3 天）
1. 集成 Monaco Editor CDN
2. 定义 G 代码语法高亮规则
3. 实现代码补全提供者
4. 添加保存快捷键（Ctrl+S）
5. 实现自动保存功能

### Phase 2.2: 加工仿真（预计 3-4 天）
1. G 代码解析器（提取运动指令）
2. Canvas 渲染引擎
3. 动画播放控制
4. 碰撞检测算法
5. 加工时间计算

### Phase 2.3: 工艺单导出（预计 2-3 天）
1. HTML 模板设计
2. PDF 生成引擎集成
3. 刀具路径图生成
4. 批量导出功能
5. 自定义 Logo 上传

---

## 📞 技术支持

### 常见问题

**Q: 忘记密码怎么办？**
A: 当前版本不支持自助重置。可以手动重置：
```bash
cd /mnt/g/projects/cad-to-gcode
source venv/bin/activate
python3 -c "
from src.storage.user_management import get_user_database
import bcrypt
db = get_user_database()
new_hash = bcrypt.hashpw('newpassword'.encode(), bcrypt.gensalt()).decode()
# 直接更新数据库
import sqlite3
conn = sqlite3.connect('data/users.db')
conn.execute('UPDATE users SET password_hash=? WHERE username=?', (new_hash, 'admin'))
conn.commit()
"
```

**Q: 如何创建新用户？**
A: 通过注册 API 或命令行：
```bash
python3 -c "
from src.storage.user_management import get_user_database
db = get_user_database()
db.create_user('username', 'email@example.com', 'password', role='user')
"
```

**Q: 用户数据如何隔离？**
A: 每个程序都关联 `user_id`，API 自动过滤：
- 普通用户：`WHERE user_id = current_user_id`
- 管理员：`WHERE 1=1`（查看全部）

---

## 📝 更新日志

### v0.4.0 (2026-04-14)
- ✅ 新增用户管理系统
- ✅ JWT Token 认证
- ✅ 多用户数据隔离
- ✅ 用户偏好设置
- ✅ 管理员权限控制

### v0.3.0 (2026-04-14)
- ✅ DXF 轮廓预览
- ✅ G 代码语法高亮增强
- ✅ 批量上传 DXF
- ✅ 程序搜索功能
- ✅ 程序删除功能

---

**文档版本：** v0.4.0  
**最后更新：** 2026-04-14  
**作者：** Hermes Agent  
**状态：** 用户系统已完成，其他功能开发中
