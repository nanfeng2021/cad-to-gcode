#!/bin/bash
# Quick Verification Script for Self-Improving Agent Configuration
# 快速验证脚本：检查自我改进代理配置是否成功

set -e

PROJECT_ROOT="/mnt/g/projects/cad-to-gcode"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "           Self-Improving Agent Configuration Verification"
echo "======================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL_COUNT++))
}

# Check 1: Skill installed
echo "[1/8] Checking skill installation..."
if hermes skills list 2>/dev/null | grep -q "self-improving-agent"; then
    check_pass "Skill 'self-improving-agent' is installed"
else
    check_fail "Skill not found. Run: hermes skills install self-improving-agent"
fi

# Check 2: Hooks config exists
echo "[2/8] Checking hooks configuration..."
if [ -f "$PROJECT_ROOT/.hermes-hooks.yaml" ]; then
    check_pass ".hermes-hooks.yaml exists"
    
    # Count enabled hooks
    HOOK_COUNT=$(grep -c "enabled: true" .hermes-hooks.yaml || echo "0")
    echo "   → $HOOK_COUNT hooks enabled"
else
    check_fail ".hermes-hooks.yaml not found"
fi

# Check 3: Required directories exist
echo "[3/8] Checking directory structure..."
DIRS_OK=true
for dir in input output processed error logs data; do
    if [ ! -d "$PROJECT_ROOT/$dir" ]; then
        check_fail "Directory '$dir' missing"
        DIRS_OK=false
    fi
done
if [ "$DIRS_OK" = true ]; then
    check_pass "All required directories exist"
fi

# Check 4: Scripts exist and are executable
echo "[4/8] Checking scripts..."
SCRIPTS=("hook_processor.py" "self_check.py" "test_pipeline.py")
for script in "${SCRIPTS[@]}"; do
    if [ -f "$PROJECT_ROOT/scripts/$script" ]; then
        check_pass "Script '$script' exists"
    else
        check_fail "Script '$script' not found"
    fi
done

# Check 5: Documentation exists
echo "[5/8] Checking documentation..."
if [ -f "$PROJECT_ROOT/docs/SELF_IMPROVING_AGENT.md" ]; then
    check_pass "Documentation exists"
else
    check_fail "Documentation not found"
fi

# Check 6: Config files valid
echo "[6/8] Checking configuration files..."
if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/.hermes-hooks.yaml'))" 2>/dev/null; then
    check_pass "Hooks config is valid YAML"
else
    check_fail "Hooks config is invalid"
fi

# Check 7: Database exists
echo "[7/8] Checking database..."
if [ -f "$PROJECT_ROOT/data/gcode.db" ]; then
    check_pass "SQLite database exists"
    
    # Count programs
    COUNT=$(sqlite3 "$PROJECT_ROOT/data/gcode.db" "SELECT COUNT(*) FROM programs;" 2>/dev/null || echo "0")
    echo "   → $COUNT programs in database"
else
    check_fail "Database not found (will be created on first run)"
fi

# Check 8: API is running (optional)
echo "[8/8] Checking API health..."
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' || echo "unknown")
    check_pass "API is running ($STATUS)"
else
    echo -e "${YELLOW}⚠${NC} API not running (optional, start with: python src/web/api.py)"
fi

# Summary
echo ""
echo "======================================================================"
echo "                           Summary"
echo "======================================================================"
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All checks passed! Configuration is successful.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Install dependencies: pip install -r requirements.txt"
    echo "  2. Start file watcher: python scripts/hook_processor.py --watch"
    echo "  3. Test with a DXF file: cp test.dxf input/"
    echo "  4. Monitor logs: tail -f logs/hook_processor.log"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some checks failed. Please review the errors above.${NC}"
    echo ""
    echo "Quick fixes:"
    echo "  - Missing skill: hermes -s self-improving-agent"
    echo "  - Missing directories: mkdir -p input output processed error logs data"
    echo "  - Invalid config: Review .hermes-hooks.yaml syntax"
    exit 1
fi
