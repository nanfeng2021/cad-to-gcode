"""
DXF File Parser for CAD to G-code Platform

Parses DXF files and extracts geometric entities for feature recognition.
Supports: LINE, CIRCLE, ARC, POLYLINE, LWPOLYLINE
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import logging
import math

try:
    import ezdxf
    from ezdxf.entities import Line, Circle, Arc, Polyline, LWPolyline
except ImportError:
    raise ImportError(
        "ezdxf is required. Install with: pip install ezdxf"
    )

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Supported DXF entity types."""
    LINE = "LINE"
    CIRCLE = "CIRCLE"
    ARC = "ARC"
    POLYLINE = "POLYLINE"
    LWPOLYLINE = "LWPOLYLINE"


@dataclass
class Point3D:
    """3D point coordinate."""
    x: float
    y: float
    z: float
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class LineEntity:
    """Line entity from DXF."""
    type: str = "line"
    start: Point3D = None
    end: Point3D = None
    layer: str = ""
    length: float = 0.0
    
    def __post_init__(self):
        if self.start and self.end:
            dx = self.end.x - self.start.x
            dy = self.end.y - self.start.y
            dz = self.end.z - self.start.z
            self.length = math.sqrt(dx*dx + dy*dy + dz*dz)


@dataclass
class CircleEntity:
    """Circle entity from DXF."""
    type: str = "circle"
    center: Point3D = None
    radius: float = 0.0
    layer: str = ""
    
    @property
    def diameter(self) -> float:
        return self.radius * 2


@dataclass
class ArcEntity:
    """Arc entity from DXF."""
    type: str = "arc"
    center: Point3D = None
    radius: float = 0.0
    start_angle: float = 0.0  # degrees
    end_angle: float = 0.0    # degrees
    layer: str = ""
    
    @property
    def sweep_angle(self) -> float:
        """Calculate sweep angle in degrees."""
        sweep = self.end_angle - self.start_angle
        if sweep < 0:
            sweep += 360
        return sweep
    
    def get_start_point(self) -> Point3D:
        """Get arc start point."""
        rad = math.radians(self.start_angle)
        return Point3D(
            x=self.center.x + self.radius * math.cos(rad),
            y=self.center.y + self.radius * math.sin(rad),
            z=self.center.z
        )
    
    def get_end_point(self) -> Point3D:
        """Get arc end point."""
        rad = math.radians(self.end_angle)
        return Point3D(
            x=self.center.x + self.radius * math.cos(rad),
            y=self.center.y + self.radius * math.sin(rad),
            z=self.center.z
        )


@dataclass
class DXFMetadata:
    """DXF file metadata."""
    filename: str = ""
    format: str = ""
    version: str = ""
    units: str = "mm"
    entity_count: int = 0


@dataclass
class ParsedGeometry:
    """Parsed geometry from DXF file."""
    metadata: DXFMetadata = None
    lines: List[LineEntity] = field(default_factory=list)
    circles: List[CircleEntity] = field(default_factory=list)
    arcs: List[ArcEntity] = field(default_factory=list)
    polylines: List[List[Point3D]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": asdict(self.metadata) if self.metadata else {},
            "entities": {
                "lines": [asdict(e) for e in self.lines],
                "circles": [asdict(e) for e in self.circles],
                "arcs": [asdict(e) for e in self.arcs],
                "polylines": [[asdict(p) for p in pl] for pl in self.polylines]
            },
            "summary": {
                "line_count": len(self.lines),
                "circle_count": len(self.circles),
                "arc_count": len(self.arcs),
                "polyline_count": len(self.polylines)
            }
        }


class DXFParser:
    """
    DXF file parser for CNC lathe parts.
    
    Extracts geometric entities and converts them to a standardized format
    suitable for feature recognition.
    """
    
    def __init__(self):
        self.doc = None
        self.msp = None
    
    def parse_file(self, filepath: str) -> ParsedGeometry:
        """
        Parse a DXF file and extract geometry.
        
        Args:
            filepath: Path to DXF file
            
        Returns:
            ParsedGeometry object with all extracted entities
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"DXF file not found: {filepath}")
        
        logger.info(f"Parsing DXF file: {filepath}")
        
        # Read DXF file
        self.doc = ezdxf.readfile(str(filepath))
        self.msp = self.doc.modelspace()
        
        # Initialize result
        result = ParsedGeometry(
            metadata=DXFMetadata(
                filename=filepath.name,
                format="DXF",
                version=self.doc.dxfversion,
                units=self._detect_units(),
                entity_count=len(self.msp)
            )
        )
        
        # Extract entities
        for entity in self.msp:
            try:
                if entity.dxftype() == 'LINE':
                    self._extract_line(entity, result)
                elif entity.dxftype() == 'CIRCLE':
                    self._extract_circle(entity, result)
                elif entity.dxftype() == 'ARC':
                    self._extract_arc(entity, result)
                elif entity.dxftype() in ['POLYLINE', 'LWPOLYLINE']:
                    self._extract_polyline(entity, result)
            except Exception as e:
                logger.warning(f"Failed to extract entity {entity.dxftype()}: {e}")
        
        logger.info(
            f"Parsed {len(result.lines)} lines, "
            f"{len(result.circles)} circles, "
            f"{len(result.arcs)} arcs, "
            f"{len(result.polylines)} polylines"
        )
        
        return result
    
    def _detect_units(self) -> str:
        """Detect drawing units from DXF metadata."""
        # Try to get INSUNITS from header
        try:
            insunits = self.doc.header.get('$INSUNITS', 1)
            unit_map = {
                1: "inches",
                2: "feet",
                4: "mm",
                5: "cm",
                6: "meters"
            }
            return unit_map.get(insunits, "mm")
        except:
            return "mm"  # Default to mm
    
    def _extract_line(self, entity: Line, result: ParsedGeometry):
        """Extract LINE entity."""
        start = entity.dxf.start
        end = entity.dxf.end
        
        line = LineEntity(
            start=Point3D(x=start[0], y=start[1], z=start[2]),
            end=Point3D(x=end[0], y=end[1], z=end[2]),
            layer=entity.dxf.layer
        )
        result.lines.append(line)
    
    def _extract_circle(self, entity: Circle, result: ParsedGeometry):
        """Extract CIRCLE entity."""
        center = entity.dxf.center
        
        circle = CircleEntity(
            center=Point3D(x=center[0], y=center[1], z=center[2]),
            radius=entity.dxf.radius,
            layer=entity.dxf.layer
        )
        result.circles.append(circle)
    
    def _extract_arc(self, entity: Arc, result: ParsedGeometry):
        """Extract ARC entity."""
        center = entity.dxf.center
        
        arc = ArcEntity(
            center=Point3D(x=center[0], y=center[1], z=center[2]),
            radius=entity.dxf.radius,
            start_angle=entity.dxf.start_angle,
            end_angle=entity.dxf.end_angle,
            layer=entity.dxf.layer
        )
        result.arcs.append(arc)
    
    def _extract_polyline(self, entity: Any, result: ParsedGeometry):
        """Extract POLYLINE or LWPOLYLINE entity."""
        points = []
        try:
            for point in entity.points():
                if len(point) >= 3:
                    points.append(Point3D(x=point[0], y=point[1], z=point[2]))
                elif len(point) == 2:
                    points.append(Point3D(x=point[0], y=point[1], z=0))
            
            if points:
                result.polylines.append(points)
        except Exception as e:
            logger.warning(f"Failed to extract polyline points: {e}")


def parse_dxf(filepath: str) -> Dict:
    """
    Convenience function to parse DXF and return dictionary.
    
    Args:
        filepath: Path to DXF file
        
    Returns:
        Dictionary with parsed geometry
    """
    parser = DXFParser()
    result = parser.parse_file(filepath)
    return result.to_dict()


if __name__ == "__main__":
    # Test parsing
    import sys
    import json
    
    if len(sys.argv) > 1:
        dxf_file = sys.argv[1]
        result = parse_dxf(dxf_file)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python dxf_parser.py <dxf_file>")
