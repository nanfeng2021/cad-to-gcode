#!/usr/bin/env python3
"""
Self-Check Script for CAD to G-code Platform
自我检测脚本：验证配置、依赖、输出和技能状态

Usage:
    python scripts/self_check.py [--verbose] [--fix]
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_check(name: str, passed: bool, details: str = ""):
    """Print check result"""
    status = f"{Colors.GREEN}✓{Colors.RESET}" if passed else f"{Colors.RED}✗{Colors.RESET}"
    print(f"{status} {name:<40}", end="")
    if details:
        print(f" - {details}")
    else:
        print()


def check_config_files() -> Tuple[bool, str]:
    """Check if configuration files exist and are valid"""
    checks = []
    
    # Check main config
    config_paths = [
        Path.home() / ".hermes" / "config.yaml",
        Path(__file__).parent.parent / "config" / "config.yaml",
        Path(__file__).parent.parent / ".hermes-hooks.yaml",
    ]
    
    config_found = False
    for path in config_paths:
        if path.exists():
            config_found = True
            checks.append(f"Config: {path}")
    
    # Check cutting rules
    cutting_rules = Path(__file__).parent.parent / "config" / "cutting_rules.yaml"
    if cutting_rules.exists():
        checks.append(f"Cutting rules: {cutting_rules}")
    else:
        return False, "Missing cutting_rules.yaml"
    
    # Check hooks config
    hooks_config = Path(__file__).parent.parent / ".hermes-hooks.yaml"
    if hooks_config.exists():
        checks.append(f"Hooks config: {hooks_config}")
    
    return config_found, "; ".join(checks) if config_found else "No config files found"


def check_dependencies() -> Tuple[bool, str]:
    """Check if Python dependencies are installed"""
    deps = {
        "ezdxf": "DXF parsing",
        "yaml": "Configuration loading",
        "fastapi": "Web API",
        "uvicorn": "ASGI server",
        "pydantic": "Data validation",
    }
    
    missing = []
    for module, desc in deps.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(f"{module} ({desc})")
    
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "All dependencies installed"


def check_project_structure() -> Tuple[bool, str]:
    """Check if project directory structure is correct"""
    required_dirs = [
        "src/ai",
        "src/cam",
        "src/core",
        "src/web",
        "data/tools",
        "data/materials",
        "input",
        "output",
        "processed",
        "error",
    ]
    
    missing = []
    for dir_path in required_dirs:
        full_path = Path(__file__).parent.parent / dir_path
        if not full_path.exists():
            missing.append(dir_path)
    
    if missing:
        return False, f"Missing directories: {', '.join(missing)}"
    return True, "Project structure complete"


def check_core_modules() -> Tuple[bool, str]:
    """Check if core modules can be imported"""
    modules = [
        ("ai.dxf_parser", "DXFParser"),
        ("ai.feature_recognition", "FeatureRecognizer"),
        ("cam.gcode_generator", "GCodeGenerator"),
        ("core.process_planning", "CuttingRulesEngine"),
        ("config_loader", "load_config"),
    ]
    
    failed = []
    base_path = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(base_path))
    
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            if not hasattr(module, class_name):
                failed.append(f"{module_name}.{class_name}: Class not found")
        except Exception as e:
            failed.append(f"{module_name}.{class_name}: {str(e)}")
    
    if failed:
        return False, f"Import errors: {'; '.join(failed[:3])}"  # Show first 3
    return True, "All core modules importable"


def check_database() -> Tuple[bool, str]:
    """Check if SQLite database exists and is accessible"""
    db_path = Path(__file__).parent.parent / "data" / "gcode.db"
    
    if not db_path.exists():
        # Try to create it
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS programs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    content TEXT NOT NULL,
                    material TEXT,
                    machine_system TEXT,
                    feature_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            return True, "Database created successfully"
        except Exception as e:
            return False, f"Cannot create database: {e}"
    
    # Test existing database
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM programs")
        count = cursor.fetchone()[0]
        conn.close()
        return True, f"Database accessible ({count} programs)"
    except Exception as e:
        return False, f"Database error: {e}"


def check_api_health() -> Tuple[bool, str]:
    """Check if FastAPI server is running and healthy"""
    import requests
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"API healthy: {data.get('status', 'unknown')}"
        else:
            return False, f"API returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "API server not running (connection refused)"
    except requests.exceptions.Timeout:
        return False, "API server timeout"
    except Exception as e:
        return False, f"API check failed: {e}"


def check_skill_installed() -> Tuple[bool, str]:
    """Check if self-improving-agent skill is installed"""
    skill_path = Path.home() / ".hermes" / "skills" / "cad-to-gcode" / "self-improving-agent"
    
    if not skill_path.exists():
        return False, "Skill not found at ~/.hermes/skills/cad-to-gcode/self-improving-agent"
    
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"
    
    # Check if skill mentions hooks
    content = skill_md.read_text()
    has_hooks = "hook" in content.lower()
    has_self_check = "self" in content.lower() and "check" in content.lower()
    
    details = []
    if has_hooks:
        details.append("Hook support ✓")
    if has_self_check:
        details.append("Self-check ✓")
    
    return True, f"Skill installed ({', '.join(details)})"


def check_hooks_config() -> Tuple[bool, str]:
    """Check if hooks configuration is valid"""
    hooks_config = Path(__file__).parent.parent / ".hermes-hooks.yaml"
    
    if not hooks_config.exists():
        return False, ".hermes-hooks.yaml not found"
    
    try:
        import yaml
        with open(hooks_config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config or 'hooks' not in config:
            return False, "No hooks defined in config"
        
        hooks = config['hooks']
        hook_count = len(hooks)
        
        # Count enabled hooks
        enabled_count = sum(1 for h in hooks if h.get('enabled', False))
        
        return True, f"{enabled_count}/{hook_count} hooks enabled"
    except Exception as e:
        return False, f"Config parse error: {e}"


def check_output_directories() -> Tuple[bool, str]:
    """Check if output directories exist and are writable"""
    dirs = ["input", "output", "processed", "error"]
    
    issues = []
    for dir_name in dirs:
        dir_path = Path(__file__).parent.parent / dir_name
        if not dir_path.exists():
            issues.append(f"{dir_name} does not exist")
        elif not os.access(dir_path, os.W_OK):
            issues.append(f"{dir_name} is not writable")
    
    if issues:
        return False, "; ".join(issues)
    return True, "All directories ready"


def run_all_checks(verbose: bool = False) -> Dict:
    """Run all checks and return results"""
    print_header("🔍 CAD to G-code Platform Self-Check")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project Root: {Path(__file__).parent.parent.absolute()}")
    
    checks = [
        ("Configuration Files", check_config_files),
        ("Python Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Core Modules", check_core_modules),
        ("SQLite Database", check_database),
        ("API Health", check_api_health),
        ("Skill Installed", check_skill_installed),
        ("Hooks Configuration", check_hooks_config),
        ("Output Directories", check_output_directories),
    ]
    
    results = {}
    passed_count = 0
    failed_count = 0
    
    for name, check_func in checks:
        try:
            passed, details = check_func()
            results[name] = {"passed": passed, "details": details}
            
            print_check(name, passed, details if verbose else "")
            
            if passed:
                passed_count += 1
            else:
                failed_count += 1
                
        except Exception as e:
            results[name] = {"passed": False, "details": str(e)}
            print_check(name, False, f"Exception: {e}")
            failed_count += 1
    
    # Summary
    print_header("Summary")
    total = passed_count + failed_count
    success_rate = (passed_count / total * 100) if total > 0 else 0
    
    print(f"Total Checks: {total}")
    print(f"{Colors.GREEN}Passed: {passed_count}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed_count}{Colors.RESET}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    overall_passed = failed_count == 0
    print(f"\nOverall Status: {Colors.GREEN}✅ ALL PASSED{Colors.RESET}" if overall_passed 
          else f"\nOverall Status: {Colors.RED}❌ SOME FAILED{Colors.RESET}")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(Path(__file__).parent.parent.absolute()),
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "success_rate": success_rate,
        "overall_passed": overall_passed,
        "checks": results
    }


def save_results(results: Dict, output_path: Path = None):
    """Save check results to JSON file"""
    if output_path is None:
        output_path = Path(__file__).parent.parent / "logs" / "self_check_results.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Results saved to: {output_path}")


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    fix_mode = "--fix" in sys.argv or "-f" in sys.argv
    
    results = run_all_checks(verbose=verbose)
    save_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_passed"] else 1)
