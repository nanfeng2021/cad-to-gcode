#!/usr/bin/env python3
"""
CAD to G-code Platform - Command Line Interface

Usage:
    cad2gcode [options] <command> [args]

Commands:
    process     Process a CAD file and generate G-code
    config      Show or edit configuration
    tools       List available cutting tools
    materials   List supported materials
    test        Run tests
    version     Show version information

Examples:
    cad2gcode process part.step --material "45#钢" --output part.nc
    cad2gcode materials
    cad2gcode config show
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.process_planning import CuttingRulesEngine, MaterialType, OperationType


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )


def cmd_process(args):
    """Process a CAD file and generate G-code."""
    from src.cam.gcode_generator import GCodeGenerator
    
    engine = CuttingRulesEngine()
    generator = GCodeGenerator(machine_system=args.system)
    
    print(f"🔧 Processing: {args.input}")
    print(f"📦 Material: {args.material}")
    print(f"🎯 Machine: {args.system}")
    
    # TODO: Implement CAD file parsing
    # For now, generate a simple test program
    gcode = generator.generate_test_program()
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(gcode, encoding='utf-8')
        print(f"✅ G-code saved to: {output_path}")
    else:
        print("\n" + "=" * 60)
        print(gcode)
        print("=" * 60)


def cmd_config(args):
    """Show or edit configuration."""
    from src.config_loader import get_config_path, load_config
    
    config_path = get_config_path()
    
    if args.action == "show":
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            sys.exit(1)
        
        print(f"📄 Config file: {config_path}")
        print("\n" + "=" * 60)
        print(config_path.read_text(encoding='utf-8'))
        print("=" * 60)
    
    elif args.action == "path":
        print(str(config_path))


def cmd_tools(args):
    """List available cutting tools."""
    engine = CuttingRulesEngine()
    
    print("🔧 Available Tool Types:\n")
    
    for tool_type, data in engine.tools.items():
        print(f"{tool_type}:")
        for tool in data.get('types', []):
            print(f"  - {tool.get('name', 'Unknown')}")
            print(f"    Applications: {', '.join(tool.get('applications', []))}")
            print(f"    Materials: {', '.join(tool.get('materials', []))}")
        print()


def cmd_materials(args):
    """List supported materials."""
    engine = CuttingRulesEngine()
    
    print("📦 Supported Materials:\n")
    
    for material in engine.list_materials():
        ops = engine.list_operations(material)
        print(f"  {material}")
        if ops:
            print(f"    Operations: {', '.join(ops)}")
        print()


def cmd_test(args):
    """Run tests."""
    import subprocess
    
    print("🧪 Running tests...\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"] + (["-x"] if args.stop_on_fail else []),
        cwd=Path(__file__).parent.parent
    )
    
    sys.exit(result.returncode)


def cmd_version(args):
    """Show version information."""
    from importlib.metadata import version, PackageNotFoundError
    
    try:
        ver = version("cad-to-gcode")
    except PackageNotFoundError:
        ver = "0.1.0-dev"
    
    print(f"cad2gcode version {ver}")
    print("Python:", sys.version.split()[0])
    print(f"Platform: {sys.platform}")


def main(argv: Optional[list] = None):
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="cad2gcode",
        description="AI-powered CAD to G-code generation for CNC lathes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "-V", "--version",
        action="store_true",
        help="Show version and exit"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process command
    proc_parser = subparsers.add_parser(
        "process",
        help="Process a CAD file and generate G-code"
    )
    proc_parser.add_argument("input", help="Input CAD file (.step, .igs, .dxf)")
    proc_parser.add_argument(
        "-m", "--material",
        default="45#钢",
        help="Material type (default: 45#钢)"
    )
    proc_parser.add_argument(
        "-s", "--system",
        default="FANUC",
        choices=["FANUC", "Siemens", "Mitsubishi"],
        help="CNC machine system (default: FANUC)"
    )
    proc_parser.add_argument(
        "-o", "--output",
        help="Output G-code file (default: stdout)"
    )
    proc_parser.set_defaults(func=cmd_process)
    
    # Config command
    conf_parser = subparsers.add_parser(
        "config",
        help="Show or edit configuration"
    )
    conf_parser.add_argument(
        "action",
        choices=["show", "path"],
        nargs="?",
        default="show",
        help="Config action (default: show)"
    )
    conf_parser.set_defaults(func=cmd_config)
    
    # Tools command
    tools_parser = subparsers.add_parser(
        "tools",
        help="List available cutting tools"
    )
    tools_parser.set_defaults(func=cmd_tools)
    
    # Materials command
    mat_parser = subparsers.add_parser(
        "materials",
        help="List supported materials"
    )
    mat_parser.set_defaults(func=cmd_materials)
    
    # Test command
    test_parser = subparsers.add_parser(
        "test",
        help="Run tests"
    )
    test_parser.add_argument(
        "-x", "--stop-on-fail",
        action="store_true",
        help="Stop on first failure"
    )
    test_parser.set_defaults(func=cmd_test)
    
    # Version command
    ver_parser = subparsers.add_parser(
        "version",
        help="Show version information"
    )
    ver_parser.set_defaults(func=cmd_version)
    
    # Parse arguments
    args = parser.parse_args(argv)
    
    # Setup logging
    setup_logging(getattr(args, 'verbose', False))
    
    # Handle version flag
    if args.version:
        cmd_version(args)
        return
    
    # Execute command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
