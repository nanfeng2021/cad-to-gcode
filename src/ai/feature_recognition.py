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

from .dxf_parser import LineEntity, CircleEntity, ArcEntity, Point3D, ParsedGeometry, TextEntity

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
        
        # For lathe parts, we typically work with the upper half profile (X > 0)
        # Filter lines to only those in the upper half plane
        valid_lines = [
            line for line in geometry.lines 
            if line.start.x > 0 or line.end.x > 0
        ]
        
        # Classify lines first
        cylinders = []
        tapers = []
        other_lines = []
        
        for line in valid_lines:
            dx = abs(line.end.x - line.start.x)
            dz = abs(line.end.z - line.start.z)
            
            # Classify based on orientation
            if dx < self.tolerance:
                # Parallel to Z-axis = cylinder
                cylinders.append(line)
            elif dz < self.tolerance:
                # Parallel to X-axis = face/shoulder (skip for now)
                other_lines.append(line)
            else:
                # Inclined = taper
                tapers.append(line)
        
        # 1. Recognize cylindrical surfaces
        cylinder_features = self._extract_cylinders(cylinders)
        feature_tree.features.extend(cylinder_features)
        
        # 2. Recognize tapers
        taper_features = self._extract_tapers(tapers)
        feature_tree.features.extend(taper_features)
        
        # 3. Recognize arc surfaces
        arc_features = self._recognize_arcs(geometry.arcs)
        feature_tree.features.extend(arc_features)
        
        # 4. Recognize grooves (simplified: look for narrow rectangular patterns)
        groove_features = self._recognize_grooves(valid_lines)
        feature_tree.features.extend(groove_features)
        
        # 5. Recognize threads from text annotations (e.g., "M30x1.5")
        thread_features = self._recognize_threads(geometry.texts, valid_lines)
        feature_tree.features.extend(thread_features)
        
        # Sort by priority (lower = machine first)
        feature_tree.features.sort(key=lambda f: f.priority)
        
        logger.info(f"Recognized {len(feature_tree.features)} features")
        
        return feature_tree
    
    def _extract_cylinders(self, lines: List[LineEntity]) -> List[MachiningFeature]:
        """Extract cylindrical features from vertical lines."""
        features = []
        
        for line in lines:
            diameter = abs(line.start.x) * 2  # X is radius in lathe coords
            length = abs(line.end.z - line.start.z)
            
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
    
    def _extract_tapers(self, lines: List[LineEntity]) -> List[MachiningFeature]:
        """Extract tapered features from inclined lines."""
        features = []
        
        for line in lines:
            dx = abs(line.end.x - line.start.x)
            dz = abs(line.end.z - line.start.z)
            
            # Calculate taper angle and diameters
            start_diameter = abs(line.start.x) * 2
            end_diameter = abs(line.end.x) * 2
            length = math.sqrt(dx*dx + dz*dz)
            
            # Taper ratio (difference in diameter / length)
            taper_ratio = abs(start_diameter - end_diameter) / length if length > 0 else 0
            
            # Calculate taper angle (in degrees)
            taper_angle = math.degrees(math.atan2(dx, dz)) if dz > 0 else 90.0
            
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
                    "taper_angle": round(taper_angle, 2),
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
        Recognize grooves by detecting凹陷 (depression) patterns.
        
        A groove is characterized by a sequence of lines forming a rectangular depression:
        - Entry: horizontal/radial line going inward (larger X → smaller X)
        - Bottom: axial line at constant smaller X (constant Z change)
        - Exit: horizontal/radial line going outward (smaller X → larger X)
        
        Pattern in XZ plane (upper half profile):
          High-X ─┐
                  ├─ Low-X (groove bottom)
          High-X ─┘
        
        Detection strategy:
        1. Find vertical lines (constant X, changing Z) that are at smaller X than neighbors
        2. Check for connecting horizontal lines at both ends
        3. Verify the pattern forms a depression (not a shoulder step)
        """
        features = []
        
        # Find the maximum X (nominal outer diameter)
        max_x = max(
            max(l.start.x, l.end.x) 
            for l in lines 
            if isinstance(l, LineEntity)
        )
        
        # Vertical lines are potential groove bottoms (constant X, axial direction)
        vertical_lines = [
            l for l in lines 
            if abs(l.end.x - l.start.x) < self.tolerance and abs(l.end.z - l.start.z) > 0.5
        ]
        
        # Horizontal lines (radial direction, constant Z)
        horizontal_lines = [
            l for l in lines 
            if abs(l.end.z - l.start.z) < self.tolerance
        ]
        
        # Look for vertical lines that could be groove bottoms
        for v_line in vertical_lines:
            groove_x = v_line.start.x  # Constant X for vertical line
            z_start = min(v_line.start.z, v_line.end.z)
            z_end = max(v_line.start.z, v_line.end.z)
            groove_width = z_end - z_start  # Width in Z direction
            
            # Groove width should be reasonable (1-8mm)
            if not (1.0 <= groove_width <= 8.0):
                continue
            
            # Check if this vertical line is at smaller X than nominal OD
            depth_from_od = max_x - groove_x
            
            # Must be a depression (at least 0.5mm below OD)
            if depth_from_od < 0.5:
                continue
            
            # Look for horizontal lines connecting to both ends of this vertical line
            z_min = min(v_line.start.z, v_line.end.z)
            z_max = max(v_line.start.z, v_line.end.z)
            
            has_entry = False  # Horizontal line entering the groove
            has_exit = False   # Horizontal line exiting the groove
            
            for h_line in horizontal_lines:
                h_z = h_line.start.z
                h_x_start = h_line.start.x
                h_x_end = h_line.end.x
                
                # Check if this horizontal line is at one end of the vertical line
                at_top = abs(h_z - z_min) < self.tolerance
                at_bottom = abs(h_z - z_max) < self.tolerance
                
                if at_top or at_bottom:
                    # Check if it connects to the groove X
                    connects_to_groove = (
                        abs(h_x_start - groove_x) < self.tolerance or
                        abs(h_x_end - groove_x) < self.tolerance
                    )
                    
                    if connects_to_groove:
                        # Check if the other end is at larger X (outer diameter)
                        other_x = h_x_end if abs(h_x_start - groove_x) < self.tolerance else h_x_start
                        if other_x > groove_x + 0.1:
                            if at_top:
                                has_entry = True
                            else:
                                has_exit = True
            
            # If we have both entry and exit, it's a groove
            if has_entry and has_exit:
                self.feature_counter += 1
                feature = MachiningFeature(
                    id=f"groove_{self.feature_counter:03d}",
                    type=FeatureType.GROOVE,
                    priority=3,
                    parameters={
                        "width": round(groove_width, 3),
                        "depth": round(depth_from_od, 3),
                        "position_z": round((z_min + z_max) / 2, 3),
                        "groove_diameter": round(groove_x * 2, 3),
                        "outer_diameter": round(max_x * 2, 3)
                    },
                    machining_area={
                        "start_x": round(groove_x, 3),
                        "end_x": round(max_x, 3),
                        "z_start": round(z_min, 3),
                        "z_end": round(z_max, 3)
                    },
                    raw_geometry={
                        "type": "groove_pattern",
                        "bottom": [v_line.start.x, v_line.start.z, v_line.end.x, v_line.end.z]
                    }
                )
                features.append(feature)
        
        return features
    
    def _recognize_threads(self, texts: List[TextEntity], lines: List[LineEntity]) -> List[MachiningFeature]:
        """
        Recognize threads from text annotations like "M30x1.5", "G1/2", etc.
        
        Thread annotation format:
        - M<major_diameter>x<pitch> (metric thread)
        - Example: M30x1.5 = 30mm major diameter, 1.5mm pitch
        
        Detection strategy:
        1. Look for TEXT entities containing thread patterns
        2. Parse the thread specification
        3. Find the corresponding cylinder at the thread location
        4. Create a thread feature with machining parameters
        """
        import re
        
        features = []
        
        # Thread pattern regex: M<diameter>x<pitch> or M<diameter>
        # Examples: M30x1.5, M20, M24x2.0
        thread_pattern = re.compile(r'M(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?', re.IGNORECASE)
        
        max_x = max(
            max(l.start.x, l.end.x) 
            for l in lines 
            if isinstance(l, LineEntity)
        ) if lines else 0
        
        for text in texts:
            match = thread_pattern.search(text.text)
            if not match:
                continue
            
            # Parse thread specification
            major_diameter = float(match.group(1))
            pitch = float(match.group(2)) if match.group(2) else 1.5  # Default pitch
            
            # Find the Z position of the text annotation
            # In lathe DXF, Y coordinate often represents Z position (machining plane is XZ)
            if text.insert_point:
                # Use Y as Z if Z is 0, otherwise use Z directly
                text_z = text.insert_point.y if abs(text.insert_point.z) < self.tolerance else text.insert_point.z
            else:
                text_z = None
                
            if text_z is None:
                logger.warning(f"Thread text '{text.text}' has no Z position")
                continue
            
            # Find the cylinder that corresponds to this thread
            # Look for vertical lines near the text Z position
            thread_line = None
            for line in lines:
                if abs(abs(line.end.x - line.start.x)) < self.tolerance:  # Vertical line
                    z_min = min(line.start.z, line.end.z)
                    z_max = max(line.start.z, line.end.z)
                    # Check if text is within the Z range of this line
                    if z_min <= text_z <= z_max:
                        thread_line = line
                        break
            
            if not thread_line:
                # Try to find any vertical line within 10mm of the text
                for line in lines:
                    if abs(abs(line.end.x - line.start.x)) < self.tolerance:
                        z_mid = (line.start.z + line.end.z) / 2
                        if abs(z_mid - text_z) < 10.0:
                            thread_line = line
                            break
            
            if not thread_line:
                logger.warning(f"Could not find cylinder for thread '{text.text}' at Z={text_z}")
                continue
            
            # Calculate thread parameters
            thread_length = abs(thread_line.end.z - thread_line.start.z)
            minor_diameter = major_diameter - 1.0825 * pitch  # H = 0.6495*P, depth = 0.5413*P*2
            
            self.feature_counter += 1
            feature = MachiningFeature(
                id=f"thread_{self.feature_counter:03d}",
                type=FeatureType.THREAD,
                priority=4,  # After grooves
                parameters={
                    "thread_type": "metric",
                    "designation": f"M{major_diameter}x{pitch}",
                    "major_diameter": round(major_diameter, 3),
                    "minor_diameter": round(minor_diameter, 3),
                    "pitch": round(pitch, 3),
                    "length": round(thread_length, 3),
                    "start_z": round(min(thread_line.start.z, thread_line.end.z), 3),
                    "end_z": round(max(thread_line.start.z, thread_line.end.z), 3)
                },
                machining_area={
                    "start_x": round(minor_diameter / 2, 3),
                    "end_x": round(major_diameter / 2, 3),
                    "z_start": round(min(thread_line.start.z, thread_line.end.z), 3),
                    "z_end": round(max(thread_line.start.z, thread_line.end.z), 3)
                },
                raw_geometry={
                    "type": "thread_annotation",
                    "text": text.text,
                    "cylinder": [thread_line.start.x, thread_line.start.z, thread_line.end.x, thread_line.end.z]
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
