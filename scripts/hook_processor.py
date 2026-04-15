#!/usr/bin/env python3
"""
Hook Processor for CAD to G-code Platform
Hook 处理器：监控文件变化、处理事件、触发自动化任务

Usage:
    python scripts/hook_processor.py [--watch] [--process FILE] [--self-check]
"""

import os
import sys
import time
import signal
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log(message: str, level: str = "INFO"):
    """Log message with timestamp and color"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "HOOK": Colors.CYAN,
    }
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}]{Colors.RESET} {message}")


class DXFFileHandler(FileSystemEventHandler):
    """Handle DXF file events"""
    
    def __init__(self, hooks_config: Dict, project_root: Path):
        self.hooks_config = hooks_config
        self.project_root = project_root
        self.debounce_time = 2  # seconds
        self.pending_files = {}
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        if not str(event.src_path).endswith('.dxf'):
            return
        
        log(f"DXF file detected: {event.src_path}", "HOOK")
        
        # Debounce - wait for file write to complete
        file_path = event.src_path
        if file_path in self.pending_files:
            return
        
        self.pending_files[file_path] = time.time()
        
        # Schedule processing after debounce
        def process_after_debounce():
            time.sleep(self.debounce_time)
            
            # Check if file still exists and is complete
            if file_path not in self.pending_files:
                return
            
            if not Path(file_path).exists():
                del self.pending_files[file_path]
                return
            
            # Process the file
            self.process_dxf_file(file_path)
            del self.pending_files[file_path]
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=process_after_debounce)
        thread.daemon = True
        thread.start()
    
    def process_dxf_file(self, file_path: str):
        """Process a single DXF file"""
        log(f"Processing DXF: {file_path}", "HOOK")
        
        try:
            # Execute the pipeline
            from ai.dxf_parser import DXFParser
            from ai.feature_recognition import recognize_features
            from cam.gcode_generator import GCodeGenerator
            
            # Step 1: Parse
            log("Step 1/3: Parsing DXF...", "INFO")
            parser = DXFParser()
            geometry = parser.parse_file(file_path)
            log(f"✓ Parsed {len(geometry.entities)} entities", "SUCCESS")
            
            # Step 2: Feature recognition
            log("Step 2/3: Recognizing features...", "INFO")
            feature_tree = recognize_features(geometry)
            log(f"✓ Recognized {feature_tree['feature_count']} features", "SUCCESS")
            
            # Step 3: Generate G-code
            log("Step 3/3: Generating G-code...", "INFO")
            filename = Path(file_path).stem
            output_path = self.project_root / "output" / f"{filename}.nc"
            
            generator = GCodeGenerator(machine_system="FANUC")
            generator.generate_from_features(
                features=feature_tree['features'],
                program_name=f"O{datetime.now().strftime('%y%m%d')}",
                part_name=filename
            )
            gcode = generator.generate()
            
            # Save output
            output_path.write_text(gcode)
            log(f"✓ G-code saved to: {output_path}", "SUCCESS")
            
            # Move input file to processed
            processed_dir = self.project_root / "processed"
            processed_dir.mkdir(exist_ok=True)
            Path(file_path).rename(processed_dir / Path(file_path).name)
            log(f"✓ Moved to processed directory", "SUCCESS")
            
            # Send notification (if configured)
            self.send_notification(filename, output_path.name, feature_tree['feature_count'])
            
        except Exception as e:
            log(f"✗ Processing failed: {e}", "ERROR")
            
            # Move to error directory
            error_dir = self.project_root / "error"
            error_dir.mkdir(exist_ok=True)
            try:
                Path(file_path).rename(error_dir / Path(file_path).name)
                log(f"Moved to error directory", "WARNING")
            except:
                pass
    
    def send_notification(self, input_file: str, output_file: str, feature_count: int):
        """Send Feishu notification"""
        try:
            # Check if webhook is configured
            webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
            if not webhook_url:
                log("Feishu webhook not configured, skipping notification", "WARNING")
                return
            
            import requests
            
            message = {
                "msg_type": "text",
                "content": {
                    "text": f"""🎉 DXF 处理完成
                    
输入文件：{input_file}
输出文件：{output_file}
识别特征：{feature_count} 个
处理时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 状态：成功"""
                }
            }
            
            response = requests.post(webhook_url, json=message, timeout=10)
            if response.status_code == 200:
                log("✓ Notification sent via Feishu", "SUCCESS")
            else:
                log(f"Notification failed: {response.status_code}", "ERROR")
                
        except Exception as e:
            log(f"Notification error: {e}", "ERROR")


def load_hooks_config() -> Dict:
    """Load hooks configuration"""
    config_paths = [
        Path(__file__).parent.parent / ".hermes-hooks.yaml",
        Path.home() / ".hermes" / "cad2gcode" / "hooks.yaml",
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    
    return {"hooks": [], "global_settings": {}}


def start_file_watcher(project_root: Path):
    """Start file system watcher"""
    log("Starting file watcher...", "HOOK")
    log(f"Watching directory: {project_root / 'input'}", "INFO")
    
    hooks_config = load_hooks_config()
    
    # Check if file watch hook is enabled
    file_watch_enabled = False
    for hook in hooks_config.get('hooks', []):
        if hook.get('name') == 'dxf_upload_processor' and hook.get('enabled'):
            file_watch_enabled = True
            break
    
    if not file_watch_enabled:
        log("File watch hook is not enabled in config", "WARNING")
        return
    
    # Setup watcher
    event_handler = DXFFileHandler(hooks_config, project_root)
    observer = Observer()
    observer.schedule(event_handler, str(project_root / "input"), recursive=False)
    observer.start()
    
    log("File watcher started. Press Ctrl+C to stop.", "SUCCESS")
    
    # Handle shutdown
    def signal_handler(sig, frame):
        log("\nShutting down file watcher...", "INFO")
        observer.stop()
        observer.join()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep running
    while True:
        time.sleep(1)


def process_single_file(file_path: str):
    """Process a single DXF file"""
    project_root = Path(__file__).parent.parent
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        log(f"File not found: {file_path}", "ERROR")
        return False
    
    handler = DXFFileHandler(load_hooks_config(), project_root)
    handler.process_dxf_file(str(file_path))
    return True


def run_self_check():
    """Run self-check script"""
    log("Running self-check...", "HOOK")
    
    self_check_script = Path(__file__).parent / "self_check.py"
    if not self_check_script.exists():
        log("Self-check script not found", "ERROR")
        return False
    
    import subprocess
    result = subprocess.run([sys.executable, str(self_check_script), "--verbose"])
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="CAD to G-code Hook Processor")
    parser.add_argument("--watch", action="store_true", help="Start file watcher mode")
    parser.add_argument("--process", type=str, metavar="FILE", help="Process a single DXF file")
    parser.add_argument("--self-check", action="store_true", help="Run self-check")
    parser.add_argument("--project-root", type=str, default=None, help="Project root directory")
    
    args = parser.parse_args()
    
    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = Path(__file__).parent.parent
    
    # Ensure required directories exist
    for dir_name in ["input", "output", "processed", "error"]:
        (project_root / dir_name).mkdir(exist_ok=True)
    
    # Execute requested action
    if args.watch:
        start_file_watcher(project_root)
    elif args.process:
        success = process_single_file(args.process)
        sys.exit(0 if success else 1)
    elif args.self_check:
        success = run_self_check()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        print("\nExamples:")
        print(f"  {sys.argv[0]} --watch                     # Start file watcher")
        print(f"  {sys.argv[0]} --process part.dxf          # Process single file")
        print(f"  {sys.argv[0]} --self-check                # Run self-check")


if __name__ == "__main__":
    main()
