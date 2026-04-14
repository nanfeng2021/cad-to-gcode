# GitHub 推送指南

## 📦 本地代码状态

当前所有代码已提交到本地 Git 仓库：

```bash
cd /mnt/g/projects/cad-to-gcode
git log --oneline -5
```

输出:
```
21d05ab docs: Add comprehensive documentation and test report
22892e9 feat: DXF parsing and feature recognition pipeline
7a9e77c feat: CAD to G-code platform MVP with persistent storage
```

---

## 🔐 配置 GitHub 认证

### 方法 1: 使用 Personal Access Token (推荐)

#### 步骤 1: 创建 Token
1. 访问 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 填写描述 (如 "cad-to-gcode deployment")
4. 勾选权限: **repo** (完整控制私有仓库)
5. 点击 **Generate token**
6. **复制生成的 token** (只显示一次！)

#### 步骤 2: 配置凭证
```bash
# 设置全局凭证存储
git config --global credential.helper store

# 推送时会提示输入用户名和 token
git push -u origin main
```

输入时:
- Username: `nanfeng2021`
- Password: 粘贴刚才复制的 **token** (不是你的 GitHub 密码！)

---

### 方法 2: 使用 SSH 密钥

#### 步骤 1: 生成 SSH 密钥
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# 按 Enter 接受默认路径
```

#### 步骤 2: 添加公钥到 GitHub
```bash
cat ~/.ssh/id_ed25519.pub
# 复制输出的内容
```

1. 访问 https://github.com/settings/keys
2. 点击 **New SSH key**
3. 粘贴公钥内容
4. 点击 **Add SSH key**

#### 步骤 3: 切换远程为 SSH
```bash
cd /mnt/g/projects/cad-to-gcode
git remote set-url origin git@github.com:nanfeng2021/cad-to-gcode.git
git push -u origin main
```

---

### 方法 3: 使用 Git Credential Manager (Windows)

如果你在 Windows 上使用 Git:

1. 下载并安装 [Git Credential Manager](https://github.com/GitCredentialManager/git-credential-manager)
2. 执行推送命令:
   ```bash
   git push -u origin main
   ```
3. 会自动弹出浏览器进行 GitHub 登录
4. 登录成功后自动完成推送

---

## 🚀 手动推送命令

配置好认证后，执行:

```bash
cd /mnt/g/projects/cad-to-gcode

# 确认远程仓库地址
git remote -v
# 应该显示:
# origin  https://github.com/nanfeng2021/cad-to-gcode.git (fetch)
# origin  https://github.com/nanfeng2021/cad-to-gcode.git (push)

# 推送到 GitHub
git push -u origin main
```

推送成功后会看到:
```
Enumerating object: XX, done.
Counting objects: 100% (XX/XX), done.
Delta compression using up to X threads
Compressing objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), XX KiB | XX MiB/s, done.
Total XX (delta XX), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (XX/XX), done.
To https://github.com/nanfeng2021/cad-to-gcode.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

---

## ✅ 验证推送

推送完成后，访问:
https://github.com/nanfeng2021/cad-to-gcode

应该能看到:
- ✅ `src/ai/dxf_parser.py`
- ✅ `src/ai/feature_recognition.py`
- ✅ `scripts/create_test_dxf.py`
- ✅ `scripts/test_pipeline.py`
- ✅ `docs/cad_to_gcode_capability_analysis.md`
- ✅ `docs/CAD_TO_GCODE_GUIDE.md`
- ✅ `tests/PIPELINE_TEST_REPORT.md`
- ✅ 以及其他项目文件

---

## 🔧 常见问题

### 问题 1: "Authentication failed"
**解决**: 
- 确保使用的是 **Personal Access Token** 而不是 GitHub 密码
- Token 需要 **repo** 权限
- 重新生成 token 并重试

### 问题 2: "Permission denied (publickey)" (SSH 方式)
**解决**:
```bash
# 测试 SSH 连接
ssh -T git@github.com

# 如果失败，重新添加 SSH 密钥到 GitHub
```

### 问题 3: "Repository not found"
**解决**:
1. 确认仓库地址正确: `https://github.com/nanfeng2021/cad-to-gcode.git`
2. 如果需要创建新仓库:
   ```bash
   # 在 GitHub 上创建空仓库 cad-to-gcode
   # 然后重新推送
   git push -u origin main
   ```

### 问题 4: 推送大文件失败
当前项目没有大文件，但如果以后遇到:
```bash
# 安装 Git LFS
git lfs install

# 跟踪大文件
git lfs track "*.dxf"

# 重新推送
git push -u origin main
```

---

## 📊 推送内容统计

预计推送内容:
- **文件数**: ~20 个
- **代码量**: ~11,000 行
- **压缩后大小**: ~500KB
- **包含**:
  - Python 源代码 (解析器、识别器、生成器)
  - 测试脚本和测试文件
  - 文档 (Markdown)
  - 配置文件

---

## 🎯 后续同步

推送完成后，以后的更新:

```bash
# 日常提交和推送
git add -A
git commit -m "feat: description"
git push  # 已配置 upstream，直接 push 即可
```

---

**创建时间**: 2026-04-14  
**仓库地址**: https://github.com/nanfeng2021/cad-to-gcode
