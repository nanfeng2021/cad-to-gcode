# Self-Improving Agent for CAD to G-code Platform

自主改进的智能体 - 通过 Hook 配置实现自动触发、执行和自我检测

## 📋 目录

- [快速开始](#快速开始)
- [配置 Hook](#配置-hook)
- [自动触发模式](#自动触发模式)
- [自我检测](#自我检测)
- [使用示例](#使用示例)
- [故障排除](#故障排除)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /mnt/g/projects/cad-to-gcode
source venv/bin/activate

# 安装文件监控依赖
pip install watchdog requests
```

### 2. 加载技能

在 Hermes CLI 中：

```bash
# 方法 1: 启动时加载
hermes -s self-improving-agent

# 方法 2: 会话中加载
/skill self-improving-agent
```

### 3. 验证安装

```bash
# 检查技能已安装
hermes skills list | grep self-improving-agent

# 运行自我检测
python scripts/self_check.py --verbose
```

---

## ⚙️ 配置 Hook

### 主配置文件

编辑 `~/.hermes/config.yaml` 添加：

```yaml
self_improving_agent:
  enabled: true
  
  file_watch:
    enabled: true
    watch_dir: "/mnt/g/projects/cad-to-gcode/input"
    pattern: "*.dxf"
  
  self_check:
    enabled: true
    checks:
      - "config_validation"
      - "output_verification"
```

### 项目级 Hook 配置

项目根目录已有 `.hermes-hooks.yaml`，包含以下预配置 Hook：

| Hook 名称 | 触发条件 | 动作 |
|---------|---------|------|
| `dxf_upload_processor` | 新 DXF 文件放入 input 目录 | 自动处理并发送通知 |
| `gcode_quality_check` | G 代码文件生成/修改 | 质量验证并记录 |
| `config_change_detector` | 配置文件变更 | 运行自我检测 |
| `batch_processor_cron` | 每 2 小时（cron） | 批量处理等待的文件 |
| `api_auto_process` | API 上传 DXF | 异步处理队列 |
| `error_learning` | 处理失败事件 | 学习并优化参数 |

### 启用飞书通知（可选）

在 `~/.hermes/.env` 中添加：

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_KEY
```

---

## 🔄 自动触发模式

### 模式 1: 文件监控（推荐）

启动文件监控守护进程：

```bash
# 后台运行
python scripts/hook_processor.py --watch &

# 或使用 nohup
nohup python scripts/hook_processor.py --watch > logs/hook_processor.log 2>&1 &
```

**工作流程：**
1. 监控 `input/` 目录
2. 检测到新的 `.dxf` 文件
3. 等待 2 秒（防抖动）
4. 自动执行转换流程
5. 移动到 `processed/` 或 `error/`
6. 发送飞书通知

### 模式 2: 定时任务

使用 Hermes cron 设置定时处理：

```bash
# 每 2 小时处理一次
hermes cron create "0 */2 * * *" \
  --prompt "使用 hook_processor 批量处理 input 目录中的所有 DXF 文件" \
  --deliver feishu

# 每天早上 9 点处理
hermes cron create "0 9 * * *" \
  --prompt "运行 batch_process.py 处理所有待处理文件"
```

### 模式 3: API 触发

FastAPI 端点已集成自动处理：

```bash
# 上传 DXF 并自动生成 G 代码
curl -X POST http://localhost:8000/gcode/upload-dxf \
  -F "file=@part.dxf" \
  -F "material=45#钢" \
  -F "machine_system=FANUC"
```

---

## 🔍 自我检测

### 运行完整检测

```bash
# 基本检测
python scripts/self_check.py

# 详细输出
python scripts/self_check.py --verbose

# 尝试自动修复
python scripts/self_check.py --fix
```

### 检测项目

| 检测项 | 说明 | 自动修复 |
|-------|------|---------|
| Configuration Files | 检查配置文件存在性 | ❌ |
| Python Dependencies | 检查依赖包安装 | ✅ (`--fix`) |
| Project Structure | 检查目录结构 | ✅ (自动创建) |
| Core Modules | 检查核心模块导入 | ❌ |
| SQLite Database | 检查数据库可访问 | ✅ (自动创建) |
| API Health | 检查 API 服务状态 | ❌ |
| Skill Installed | 检查技能已加载 | ❌ |
| Hooks Configuration | 检查 Hook 配置 | ❌ |
| Output Directories | 检查输出目录 | ✅ (自动创建) |

### 检测结果示例

```
======================================================================
                🔍 CAD to G-code Platform Self-Check                
======================================================================

Timestamp: 2026-04-15T15:30:45.123456
Project Root: /mnt/g/projects/cad-to-gcode

✓ Configuration Files                      - Config: 3 files found
✓ Python Dependencies                      - All dependencies installed
✓ Project Structure                        - Project structure complete
✓ Core Modules                             - All core modules importable
✓ SQLite Database                          - Database accessible (15 programs)
✗ API Health                               - API server not running (connection refused)
✓ Skill Installed                          - Skill installed (Hook support ✓, Self-check ✓)
✓ Hooks Configuration                      - 5/6 hooks enabled
✓ Output Directories                       - All directories ready

======================================================================
                              Summary                               
======================================================================

Total Checks: 9
Passed: 8
Failed: 1
Success Rate: 88.9%

Overall Status: ❌ SOME FAILED
```

---

## 📖 使用示例

### 示例 1: 手动处理单个文件

```bash
# 直接处理
python scripts/hook_processor.py --process /path/to/part.dxf

# 或使用测试脚本
python scripts/test_pipeline.py tests/test_dxf_files/simple_shaft.dxf
```

### 示例 2: 启动自动监控

```bash
# 终端 1: 启动文件监控
cd /mnt/g/projects/cad-to-gcode
python scripts/hook_processor.py --watch

# 终端 2: 放入 DXF 文件
cp ~/downloads/shaft.dxf input/

# 观察输出目录
ls -la output/
```

### 示例 3: 查看处理日志

```bash
# 实时监控
tail -f logs/hook_processor.log

# 查看最近的错误
grep -i "error\|failed" logs/hook_processor.log | tail -10
```

### 示例 4: 批量处理队列

```bash
# 处理所有等待的文件
python scripts/batch_process.py

# 查看处理报告
cat logs/batch_report.json | jq
```

### 示例 5: 从飞书机器人触发

在飞书中向机器人发送：

```
处理 input 目录中的所有 DXF 文件
```

机器人会自动执行批量处理并返回报告。

---

## 🛠️ 故障排除

### 问题 1: 文件监控未触发

**症状**: 放入 DXF 文件后没有反应

**解决方案**:
```bash
# 1. 检查监控进程
ps aux | grep hook_processor

# 2. 检查目录权限
ls -la input/

# 3. 手动测试
python scripts/hook_processor.py --process input/test.dxf

# 4. 查看详细日志
tail -f logs/hook_processor.log
```

### 问题 2: 自我检测失败

**症状**: `self_check.py` 报告多个失败

**解决方案**:
```bash
# 1. 运行修复模式
python scripts/self_check.py --fix

# 2. 重新安装依赖
pip install -r requirements.txt

# 3. 重建数据库
rm data/gcode.db
python scripts/self_check.py

# 4. 重启 API 服务
python src/web/api.py &
```

### 问题 3: 飞书通知未发送

**症状**: 处理完成但没有收到通知

**解决方案**:
```bash
# 1. 检查 webhook 配置
echo $FEISHU_WEBHOOK_URL

# 2. 测试 webhook
curl -X POST $FEISHU_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"Test"}}'

# 3. 查看通知日志
grep -i "feishu\|notification" logs/hook_processor.log
```

### 问题 4: G 代码验证失败

**症状**: 生成的 G 代码无法通过质量检测

**解决方案**:
```bash
# 1. 手动验证
python scripts/validate_gcode.py output/part.nc

# 2. 查看生成器日志
grep -A 10 "G-code generation" logs/cad2gcode.log

# 3. 使用备用策略
export GCODE_GENERATOR_FALLBACK=simple_shaft
python scripts/hook_processor.py --process input/part.dxf
```

---

## 📊 性能指标

### 监控关键指标

```bash
# 查看处理统计
cat logs/performance_metrics.jsonl | jq -s '
  {
    total_files: length,
    avg_processing_time: (map(.processing_time) | add / length),
    success_rate: (map(select(.status == "success")) | length) / length * 100
  }
'
```

### 自动优化

技能会根据历史数据自动优化：

- **批处理大小**: 根据内存使用情况调整
- **超时时间**: 根据文件复杂度调整
- **容差参数**: 根据识别准确率调整

---

## 🔗 相关文件

| 文件 | 用途 |
|------|------|
| `~/.hermes/skills/cad-to-gcode/self-improving-agent/SKILL.md` | 技能文档 |
| `/mnt/g/projects/cad-to-gcode/.hermes-hooks.yaml` | Hook 配置 |
| `/mnt/g/projects/cad-to-gcode/scripts/hook_processor.py` | Hook 处理器 |
| `/mnt/g/projects/cad-to-gcode/scripts/self_check.py` | 自我检测脚本 |
| `/mnt/g/projects/cad-to-gcode/scripts/test_pipeline.py` | 端到端测试 |
| `/mnt/g/projects/cad-to-gcode/scripts/validate_gcode.py` | G 代码验证 |

---

## ✅ 验证清单

完成以下检查确认配置成功：

- [ ] 技能已安装：`hermes skills list | grep self-improving-agent`
- [ ] Hook 配置存在：`test -f .hermes-hooks.yaml`
- [ ] 文件监控可启动：`python scripts/hook_processor.py --watch`
- [ ] 自我检测通过：`python scripts/self_check.py`
- [ ] 测试文件可处理：`python scripts/test_pipeline.py tests/test_dxf_files/simple_shaft.dxf`
- [ ] 飞书通知配置（可选）：`echo $FEISHU_WEBHOOK_URL`

全部完成后，技能应该能够：
- ✅ 自动检测新 DXF 文件
- ✅ 独立执行转换流程
- ✅ 生成有效的 G 代码
- ✅ 发送成功/失败通知
- ✅ 记录学习数据供未来改进

---

**最后更新**: 2026-04-15  
**版本**: 1.0.0  
**作者**: Hermes Agent + Nanfeng
