"""
Configuration loader for CAD to G-code platform.
Follows Hermes Agent config patterns.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def get_hermes_home() -> Path:
    """Get Hermes home directory (profile-aware)."""
    if env := os.environ.get("HERMES_HOME"):
        return Path(env)
    return Path.home() / ".hermes"


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_config_path() -> Path:
    """Get path to configuration file."""
    # Check environment variable first
    if env_path := os.environ.get("CAD2GCODE_CONFIG"):
        return Path(env_path)
    
    # Check project directory
    project_config = get_project_root() / "config" / "config.yaml"
    if project_config.exists():
        return project_config
    
    # Fallback to user config
    user_config = get_hermes_home() / "cad2gcode" / "config.yaml"
    return user_config


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file (optional, uses default if not provided)
    
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = get_config_path()
    
    if not config_path.exists():
        # Return default config
        return get_default_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Merge with defaults
        defaults = get_default_config()
        return deep_merge(defaults, config)
    
    except Exception as e:
        print(f"⚠️  Warning: Failed to load config from {config_path}: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Get default configuration values."""
    return {
        "project": {
            "name": "cad-to-gcode",
            "version": "0.1.0",
            "target_machine": "FANUC 2-axis lathe",
            "supported_formats": ["step", "igs", "dxf", "dwg"],
        },
        "model": {
            "feature_recognition_model": "resnet50",
            "process_planning_model": "rule-based-v1",
            "provider": "local",
            "context_length": 4096,
        },
        "terminal": {
            "backend": "local",
            "cwd": ".",
            "timeout": 180,
            "shell": "bash",
        },
        "database": {
            "tools_db_path": "data/tools/tools.db",
            "materials_db_path": "data/materials/materials.db",
            "cutting_rules_path": "config/cutting_rules.yaml",
        },
        "web": {
            "host": "0.0.0.0",
            "port": 8000,
            "debug": True,
            "max_upload_size_mb": 50,
        },
        "gcode": {
            "default_system": "FANUC",
            "supported_systems": ["FANUC", "Siemens", "Mitsubishi", "GSK", "HNC"],
            "include_comments": True,
            "include_tool_changes": True,
            "safety_checks": True,
        },
        "ai": {
            "enable_deep_learning": False,
            "training_data_path": "data/training",
            "model_cache_path": ".cache/models",
            "batch_size": 32,
            "learning_rate": 0.001,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "logs/cad2gcode.log",
            "max_size_mb": 10,
            "backup_count": 5,
        },
        "security": {
            "tirith_enabled": True,
            "allowed_file_extensions": [".step", ".igs", ".dxf", ".dwg", ".stp", ".ige"],
            "max_file_size_mb": 50,
            "scan_for_macros": True,
        },
        "checkpoints": {
            "enabled": True,
            "max_snapshots": 50,
            "checkpoint_dir": ".checkpoints",
        },
    }


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary to merge on top
    
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def save_config(config: Dict[str, Any], config_path: Optional[Path] = None):
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save to (optional, uses default if not provided)
    """
    if config_path is None:
        config_path = get_config_path()
    
    # Create parent directories
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ Config saved to: {config_path}")


# Example usage
if __name__ == "__main__":
    config = load_config()
    print("Loaded configuration:")
    print(f"  Project: {config['project']['name']} v{config['project']['version']}")
    print(f"  Target machine: {config['project']['target_machine']}")
    print(f"  Web interface: {config['web']['host']}:{config['web']['port']}")
    print(f"  Logging level: {config['logging']['level']}")
