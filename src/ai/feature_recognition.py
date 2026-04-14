"""
Feature Recognition Engine for CAD to G-code Platform

Recognizes machining features from parsed DXF geometry:
- External cylinders (parallel to Z-axis lines)
- Tapers (inclined lines)
- Arc surfaces
- Grooves (narrow depressions)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import math
import logging

from .dxf_parser import LineEntity, CircleEntity, ArcEntity, Point3D, ParsedGeometry

logger = logging.getLogger(__name__)


class FeatureType(str, Enum):
    """Machining feature types."""
    EXTERNAL_CYLINDER = "external_cylinder"
    TAPER = "taper"
    ARC_SURFACE = "arc_surface"
    GROOVE = "groove"
    THREAD = "thread"
    CHAMFER = "chamfer"
    FILLET = "fillet"


@dataclass
class MachiningFeature:
    """Represents a recognized machining feature."""
    id: str
    type: FeatureType
    priority: int  # Lower = machine first
    parameters: Dict = field(default_factory=dict)
    machining_area: Dict = field(default_factory=dict)
    raw_geometry: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority,
            "parameters": self.parameters,
            "machining_area": self.machining_area,
            "raw_geometry": self.raw_geometry
        }


@dataclass
class FeatureTree:
    """Complete feature tree for a part."""
    part_id: str = ""
    features: List[MachiningFeature] = field(default_factory=list)
    setup_info: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "part_id": self.part_id,
            "features": [f.to_dict() for f in self.features],
            "setup_info": self.setup_info,
            "feature_count": len(self.features)
        }


class FeatureRecognizer:
    """
    Recognizes machining features from DXF geometry.
    
    Uses rule-based approach to identify:
    - Cylindrical surfaces (lines parallel to Z-axis)
    - Tapered surfaces (inclined lines)
    - Arc surfaces (ARC/CIRCLE entities)
    - Grooves (narrow rectangular depressions)
    """
    
    def __init__(self, tolerance: float = 0.001):
        """
        Initialize feature recognizer.
        
        Args:
            tolerance: Geometric tolerance for comparisons (mm)
        """
        self.tolerance = tolerance
        self.feature_counter = 0
    
    def recognize(self, geometry: ParsedGeometry) -> FeatureTree:
        """
        Recognize features from parsed geometry.
        
        Args:
            geometry: ParsedGeometry from DXF parser
            
        Returns:
            FeatureTree with all recognized features
        """
        logger.info("Starting feature recognition...")
        
        feature_tree = FeatureTree(
            part_id=geometry.metadata.filename.replace('.dxf', ''),
            setup_info={
                "units": geometry.metadata.units,
                "source_file": geometry.metadata.filename
            }
        )
        
        # For lathe parts, we typically work with the upper half profile (Y > 0)
        # Extract the outer profile from lines and arcs
        
        # 1. Recognize cylindrical surfaces from lines
        cylinder_features = self._recognize_cylinders(geometry.lines)
        feature_tree.features.extend(cylinder_features)
        
        # 2. Recognize tapers from inclined lines
        taper_features = self._recognize_tapers(geometry.lines)
        feature_tree.features.extend(taper_features)
        
        # 3. Recognize arc surfaces
        arc_features = self._recognize_arcs(geometry.arcs)
        feature_tree.features.extend(arc_features)
        
        # 4. Recognize grooves (simplified: look for narrow rectangular patterns)
        groove_features = self._recognize_grooves(geometry.lines)
        feature_tree.features.extend(groove_features)
        
        # Sort by priority (lower = machine first)
        feature_tree.features.sort(key=lambda f: f.priority)
        
        logger.info(f"Recognized {len(feature_tree.features)} features")
        
        return feature_tree
    
    def _recognize_cylinders(self, lines: List[LineEntity]) -> List[MachiningFeature]:
        """Recognize external cylindrical surfaces."""
        features = []
        
        for line in lines:
            # Check if line is parallel to Z-axis (X coordinates nearly equal)
            if abs(line.end.x - line.start.x) < self.tolerance:
                # This is a vertical line in XZ plane = cylindrical surface
                diameter = abs(line.start.x) * 2  # X is radius in lathe coords
                length = abs(line.end.z - line.start.z)
                
                # Only consider lines in upper half (Y > 0 or X > 0)
                if line.start.x > 0:
                    self.feature_counter += 1
                    feature = MachiningFeature(
                        id=f"cyl_{self.feature_counter:03d}",
                        type=FeatureType.EXTERNAL_CYLINDER,
                        priority=1,  # Cylinders machined first
                        parameters={
                            "diameter": round(diameter, 3),
                            "length": round(length, 3),
                            "start_z": round(min(line.start.z, line.end.z), 3),
                            "end_z": round(max(line.start.z, line.end.z), 3)
                        },
                        machining_area={
                            "start_x": round(line.start.x, 3),
                            "end_x": round(line.end.x, 3),
                            "start_z": round(line.start.z, 3),
                            "end_z": round(line.end.z, 3)
                        },
                        raw_geometry={
                            "type": "line",
                            "start": [line.start.x, line.start.y, line.start.z],
                            "end": [line.end.x, line.end.y, line.end.z]
                        }
                    )
                    features.append(feature)
        
        return features
    
    def _recognize_tapers(self, lines: List[LineEntity]) -> List[MachiningFeature]:
        """Recognize tapered surfaces from inclined lines."""
        features = []
        
        for line in lines:
            # Skip lines parallel to axes
            dx = abs(line.end.x - line.start.x)
            dz = abs(line.end.z - line.start.z)
            
            if dx < self.tolerance or dz < self.tolerance:
                continue  # Parallel to axis, not a taper
            
            # Calculate taper angle and diameters
            start_diameter = abs(line.start.x) * 2
            end_diameter = abs(line.end.x) * 2
            length = math.sqrt(dx*dx + dz*dz)
            
            # Taper ratio (difference in diameter / length)
            taper_ratio = abs(start_diameter - end_diameter) / length if length > 0 else 0
            
            # Only consider lines in upper half
            if line.start.x > 0 and line.end.x > 0:
                self.feature_counter += 1
                feature = MachiningFeature(
                    id=f"taper_{self.feature_counter:03d}",
                    type=FeatureType.TAPER,
                    priority=1,
                    parameters={
                        "start_diameter": round(start_diameter, 3),
                        "end_diameter": round(end_diameter, 3),
                        "length": round(length, 3),
                        "taper_ratio": round(taper_ratio, 4),
                        "start_z": round(min(line.start.z, line.end.z), 3),
                        "end_z": round(max(line.start.z, line.end.z), 3)
                    },
                    machining_area={
                        "start_x": round(line.start.x, 3),
                        "end_x": round(line.end.x, 3),
                        "start_z": round(line.start.z, 3),
                        "end_z": round(line.end.z, 3)
                    },
                    raw_geometry={
                        "type": "line",
                        "start": [line.start.x, line.start.y, line.start.z],
                        "end": [line.end.x, line.end.y, line.end.z]
                    }
                )
                features.append(feature)
        
        return features
    
    def _recognize_arcs(self, arcs: List[ArcEntity]) -> List[MachiningFeature]:
        """Recognize arc/circular surfaces."""
        features = []
        
        for arc in arcs:
            # Only consider arcs in upper half plane
            if arc.center.x > 0 or (arc.center.x == 0 and arc.radius > 0):
                self.feature_counter += 1
                
                # Determine if convex or concave
                is_convex = arc.sweep_angle <= 180
                
                feature = MachiningFeature(
                    id=f"arc_{self.feature_counter:03d}",
                    type=FeatureType.ARC_SURFACE,
                    priority=2,  # Arcs after cylinders/tapers
                    parameters={
                        "radius": round(arc.radius, 3),
                        "center_x": round(arc.center.x, 3),
                        "center_z": round(arc.center.z, 3),
                        "start_angle": round(arc.start_angle, 2),
                        "end_angle": round(arc.end_angle, 2),
                        "sweep_angle": round(arc.sweep_angle, 2),
                        "convex": is_convex
                    },
                    machining_area={
                        "start_point": arc.get_start_point().to_tuple(),
                        "end_point": arc.get_end_point().to_tuple()
                    },
                    raw_geometry={
                        "type": "arc",
                        "center": [arc.center.x, arc.center.y, arc.center.z],
                        "radius": arc.radius,
                        "start_angle": arc.start_angle,
                        "end_angle": arc.end_angle
                    }
                )
                features.append(feature)
        
        return features
    
    def _recognize_grooves(self, lines: List[LineEntity]) -> List[MachiningFeature]:
        """
        Recognize grooves (simplified heuristic).
        
        Looks for narrow rectangular patterns:
        - Short horizontal line (groove bottom)
        - Two vertical lines (groove sides)
        """
        features = []
        
        # Group lines by Z coordinate to find potential groove patterns
        horizontal_lines = []
        vertical_lines = []
        
        for line in lines:
            dx = abs(line.end.x - line.start.x)
            dz = abs(line.end.z - line.start.z)
            
            if dz < self.tolerance and dx > 0.5:  # Horizontal line
                horizontal_lines.append(line)
            elif dx < self.tolerance and dz > 0.5:  # Vertical line
                vertical_lines.append(line)
        
        # Simple groove detection: look for short horizontal lines
        # that could be groove bottoms (width < 5mm typically)
        for line in horizontal_lines:
            width = abs(line.end.x - line.start.x)
            
            if 0.5 < width < 5.0:  # Potential groove width
                # Check if there are vertical lines at the ends
                z_level = line.start.z
                x_start = min(line.start.x, line.end.x)
                x_end = max(line.start.x, line.end.x)
                
                has_left_wall = any(
                    abs(v_line.start.x - x_start) < self.tolerance and
                    abs(v_line.start.z - z_level) < self.tolerance
                    for v_line in vertical_lines
                )
                
                has_right_wall = any(
                    abs(v_line.start.x - x_end) < self.tolerance and
                    abs(v_line.start.z - z_level) < self.tolerance
                    for v_line in vertical_lines
                )
                
                if has_left_wall and has_right_wall:
                    self.feature_counter += 1
                    depth = max(
                        abs(v_line.end.z - v_line.start.z)
                        for v_line in vertical_lines
                        if abs(v_line.start.x - x_start) < self.tolerance or
                           abs(v_line.start.x - x_end) < self.tolerance
                    )
                    
                    feature = MachiningFeature(
                        id=f"groove_{self.feature_counter:03d}",
                        type=FeatureType.GROOVE,
                        priority=3,  # Grooves after OD turning
                        parameters={
                            "width": round(width, 3),
                            "depth": round(depth, 3),
                            "position_z": round(z_level, 3),
                            "start_x": round(x_start, 3),
                            "end_x": round(x_end, 3)
                        },
                        machining_area={
                            "start_x": round(x_start, 3),
                            "end_x": round(x_end, 3),
                            "z_level": round(z_level, 3)
                        },
                        raw_geometry={
                            "type": "groove_pattern",
                            "bottom": [line.start.x, line.start.z, line.end.x, line.end.z]
                        }
                    )
                    features.append(feature)
        
        return features


def recognize_features(geometry: ParsedGeometry) -> Dict:
    """
    Convenience function to recognize features from parsed geometry.
    
    Args:
        geometry: ParsedGeometry from DXF parser
        
    Returns:
        Dictionary with feature tree
    """
    recognizer = FeatureRecognizer()
    feature_tree = recognizer.recognize(geometry)
    return feature_tree.to_dict()


if __name__ == "__main__":
    # Test feature recognition
    import sys
    import json
    from dxf_parser import parse_dxf
    
    if len(sys.argv) > 1:
        dxf_file = sys.argv[1]
        geometry = parse_dxf(dxf_file)
        
        # Convert back to ParsedGeometry for testing
        # (In production, use the actual objects)
        print("Feature recognition requires ParsedGeometry object")
        print("Use the recognize_features() function in your code")
    else:
        print("Usage: python feature_recognition.py <dxf_file>")
