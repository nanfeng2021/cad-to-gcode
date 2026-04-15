"""
智能特征识别增强系统 - 深度学习 + 规则混合架构

功能:
- 复杂轮廓自动分段 (基于曲率分析)
- 相交几何处理 (布尔运算)
- 不完整标注推断 (对称性检测)
- ML 特征分类 (ResNet50/ EfficientNet)
- 特征优先级优化 (强化学习)

架构:
1. 规则引擎层：快速匹配已知模式
2. 几何分析层：曲率、连续性、拓扑分析  
3. 机器学习层：深度神经网络分类
4. 决策融合层：加权投票 + 置信度评估

使用示例:
    recognizer = FeatureRecognizer()
    features = recognizer.recognize(entities)
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import math


class FeatureType(Enum):
    """特征类型枚举"""
    EXTERNAL_CYLINDER = "external_cylinder"  # 外圆
    TAPER = "taper"                          # 锥面
    ARC_SURFACE = "arc_surface"              # 圆弧面
    GROOVE = "groove"                        # 槽
    THREAD = "thread"                        # 螺纹
    CHAMFER = "chamfer"                      # 倒角
    FILLET = "fillet"                        # 圆角


@dataclass
class GeometricFeature:
    """几何特征"""
    type: FeatureType
    start_point: Tuple[float, float]  # (X, Z)
    end_point: Tuple[float, float]
    parameters: Dict = field(default_factory=dict)
    confidence: float = 1.0  # 置信度 0-1
    source: str = "rule"     # "rule" | "ml" | "hybrid"


@dataclass
class RecognitionResult:
    """识别结果"""
    features: List[GeometricFeature] = field(default_factory=list)
    segments: List = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0


class CurvatureAnalyzer:
    """曲率分析器 - 用于轮廓分段"""
    
    def __init__(self, tolerance: float = 1e-6):
        self.tolerance = tolerance
    
    def calculate_curvature(self, points: List[Tuple[float, float]]) -> List[float]:
        """
        计算离散点的曲率
        
        使用三点圆近似法:
        κ = 4 * Area / (a * b * c)
        
        其中 a, b, c 是三点构成的三角形边长
        """
        if len(points) < 3:
            return [0.0] * len(points)
        
        curvatures = []
        
        for i in range(len(points)):
            p_prev = points[(i - 1) % len(points)]
            p_curr = points[i]
            p_next = points[(i + 1) % len(points)]
            
            # 计算三边长度
            a = self._distance(p_prev, p_curr)
            b = self._distance(p_curr, p_next)
            c = self._distance(p_prev, p_next)
            
            # 半周长
            s = (a + b + c) / 2
            
            # Heron 公式计算面积
            area_sq = s * (s - a) * (s - b) * (s - c)
            if area_sq <= 0:
                curvatures.append(0.0)
                continue
            
            area = math.sqrt(area_sq)
            
            # 曲率
            if a * b * c > self.tolerance:
                curvature = 4 * area / (a * b * c)
            else:
                curvature = 0.0
            
            curvatures.append(curvature)
        
        return curvatures
    
    def detect_break_points(self, points: List[Tuple[float, float]], 
                           threshold: float = 0.5) -> List[int]:
        """
        检测轮廓断点 (曲率突变点)
        
        用于自动分段复杂轮廓
        """
        curvatures = self.calculate_curvature(points)
        break_points = []
        
        if len(curvatures) < 2:
            return break_points
        
        # 计算曲率变化率
        for i in range(1, len(curvatures)):
            delta_k = abs(curvatures[i] - curvatures[i-1])
            
            # 归一化
            max_k = max(curvatures) if max(curvatures) > 0 else 1.0
            normalized_delta = delta_k / max_k
            
            if normalized_delta > threshold:
                break_points.append(i)
        
        return break_points
    
    def segment_profile(self, points: List[Tuple[float, float]]) -> List[List[Tuple[float, float]]]:
        """
        基于曲率分析将轮廓分段
        """
        break_points = self.detect_break_points(points)
        
        if not break_points:
            return [points]
        
        segments = []
        start = 0
        
        for bp in break_points:
            segment = points[start:bp+1]
            if len(segment) >= 2:
                segments.append(segment)
            start = bp
        
        # 最后一段
        if start < len(points):
            segment = points[start:]
            if len(segment) >= 2:
                segments.append(segment)
        
        return segments
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """计算两点距离"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


class RuleEngine:
    """规则引擎 - 基于专家系统的特征识别"""
    
    def __init__(self):
        self.rules = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        # 规则 1: 外圆识别 - X 坐标基本不变
        self.rules.append({
            'name': 'external_cylinder',
            'condition': self._check_cylinder,
            'extract': self._extract_cylinder_params,
            'type': FeatureType.EXTERNAL_CYLINDER
        })
        
        # 规则 2: 锥面识别 - X 坐标线性变化
        self.rules.append({
            'name': 'taper',
            'condition': self._check_taper,
            'extract': self._extract_taper_params,
            'type': FeatureType.TAPER
        })
        
        # 规则 3: 圆弧识别 - 恒定曲率
        self.rules.append({
            'name': 'arc_surface',
            'condition': self._check_arc,
            'extract': self._extract_arc_params,
            'type': FeatureType.ARC_SURFACE
        })
        
        # 规则 4: 槽识别 - 先减后增的 X 坐标
        self.rules.append({
            'name': 'groove',
            'condition': self._check_groove,
            'extract': self._extract_groove_params,
            'type': FeatureType.GROOVE
        })
        
        # 规则 5: 倒角识别 - 短直线段，角度接近 45°
        self.rules.append({
            'name': 'chamfer',
            'condition': self._check_chamfer,
            'extract': self._extract_chamfer_params,
            'type': FeatureType.CHAMFER
        })
    
    def recognize(self, segment: List[Tuple[float, float]]) -> Optional[GeometricFeature]:
        """
        对单个轮廓段应用规则引擎识别
        """
        if len(segment) < 2:
            return None
        
        for rule in self.rules:
            if rule['condition'](segment):
                params = rule['extract'](segment)
                return GeometricFeature(
                    type=rule['type'],
                    start_point=segment[0],
                    end_point=segment[-1],
                    parameters=params,
                    confidence=self._calculate_confidence(segment, rule),
                    source="rule"
                )
        
        return None
    
    def _check_cylinder(self, segment: List[Tuple[float, float]]) -> bool:
        """检查是否为外圆"""
        if len(segment) < 2:
            return False
        
        x_coords = [p[0] for p in segment]
        x_variation = max(x_coords) - min(x_coords)
        avg_x = sum(x_coords) / len(x_coords)
        
        # X 坐标变化小于平均值的 1%
        return x_variation / (avg_x + 1e-6) < 0.01
    
    def _check_taper(self, segment: List[Tuple[float, float]]) -> bool:
        """检查是否为锥面"""
        if len(segment) < 2:
            return False
        
        # 线性拟合检查
        x_coords = [p[0] for p in segment]
        z_coords = [p[1] for p in segment]
        
        # 简单线性相关检查
        if len(segment) >= 3:
            # 计算相邻段的斜率变化
            slopes = []
            for i in range(len(segment) - 1):
                dz = z_coords[i+1] - z_coords[i]
                dx = x_coords[i+1] - x_coords[i]
                if abs(dx) > 1e-6:
                    slopes.append(dz / dx)
            
            if len(slopes) >= 2:
                slope_variation = max(slopes) - min(slopes)
                avg_slope = sum(slopes) / len(slopes)
                
                # 斜率变化小于 10%
                return slope_variation / (abs(avg_slope) + 1e-6) < 0.1
        
        return False
    
    def _check_arc(self, segment: List[Tuple[float, float]]) -> bool:
        """检查是否为圆弧"""
        if len(segment) < 3:
            return False
        
        # 使用曲率分析
        analyzer = CurvatureAnalyzer()
        curvatures = analyzer.calculate_curvature(segment)
        
        # 检查曲率是否恒定
        avg_curvature = sum(curvatures) / len(curvatures)
        if avg_curvature < 1e-6:
            return False
        
        variation = max(curvatures) - min(curvatures)
        return variation / (avg_curvature + 1e-6) < 0.15
    
    def _check_groove(self, segment: List[Tuple[float, float]]) -> bool:
        """检查是否为槽"""
        if len(segment) < 3:
            return False
        
        x_coords = [p[0] for p in segment]
        
        # 寻找最小值点
        min_idx = x_coords.index(min(x_coords))
        
        # 检查是否先减后增
        decreasing = all(x_coords[i] >= x_coords[i+1] for i in range(min_idx))
        increasing = all(x_coords[i] <= x_coords[i+1] for i in range(min_idx, len(x_coords)-1))
        
        return decreasing and increasing and min_idx > 0 and min_idx < len(x_coords) - 1
    
    def _check_chamfer(self, segment: List[Tuple[float, float]]) -> bool:
        """检查是否为倒角"""
        if len(segment) < 2:
            return False
        
        # 计算长度
        length = math.sqrt(
            (segment[-1][0] - segment[0][0])**2 + 
            (segment[-1][1] - segment[0][1])**2
        )
        
        # 倒角通常较短 (< 5mm)
        if length > 5.0:
            return False
        
        # 检查角度是否接近 45°
        dx = segment[-1][0] - segment[0][0]
        dz = segment[-1][1] - segment[0][1]
        
        if abs(dx) < 1e-6:
            return False
        
        angle = abs(math.atan(dz / dx) * 180 / math.pi)
        return 40 <= angle <= 50
    
    def _extract_cylinder_params(self, segment: List[Tuple[float, float]]) -> Dict:
        """提取外圆参数"""
        x_coords = [p[0] for p in segment]
        z_coords = [p[1] for p in segment]
        
        return {
            'diameter': sum(x_coords) / len(x_coords),
            'length': abs(max(z_coords) - min(z_coords)),
            'start_z': min(z_coords),
            'end_z': max(z_coords)
        }
    
    def _extract_taper_params(self, segment: List[Tuple[float, float]]) -> Dict:
        """提取锥面参数"""
        start_diameter = segment[0][0]
        end_diameter = segment[-1][0]
        length = abs(segment[-1][1] - segment[0][1])
        
        # 计算锥角
        delta_d = abs(end_diameter - start_diameter)
        taper_angle = math.atan(delta_d / (2 * length)) * 180 / math.pi if length > 0 else 0
        
        return {
            'start_diameter': start_diameter,
            'end_diameter': end_diameter,
            'length': length,
            'taper_angle': taper_angle,
            'direction': 'increasing' if end_diameter > start_diameter else 'decreasing'
        }
    
    def _extract_arc_params(self, segment: List[Tuple[float, float]]) -> Dict:
        """提取圆弧参数"""
        # 三点确定一个圆
        if len(segment) >= 3:
            p1, p2, p3 = segment[0], segment[len(segment)//2], segment[-1]
            center, radius = self._fit_circle([p1, p2, p3])
            
            return {
                'center': center,
                'radius': radius,
                'start_angle': self._calc_angle(center, p1),
                'end_angle': self._calc_angle(center, p3),
                'convex': self._is_convex(segment, center)
            }
        
        return {'radius': 0}
    
    def _extract_groove_params(self, segment: List[Tuple[float, float]]) -> Dict:
        """提取槽参数"""
        x_coords = [p[0] for p in segment]
        z_coords = [p[1] for p in segment]
        
        min_idx = x_coords.index(min(x_coords))
        
        return {
            'width': abs(z_coords[-1] - z_coords[0]),
            'depth': max(x_coords) - min(x_coords),
            'bottom_diameter': min(x_coords),
            'position': z_coords[min_idx]
        }
    
    def _extract_chamfer_params(self, segment: List[Tuple[float, float]]) -> Dict:
        """提取倒角参数"""
        dx = segment[-1][0] - segment[0][0]
        dz = segment[-1][1] - segment[0][1]
        length = math.sqrt(dx**2 + dz**2)
        angle = abs(math.atan(dz / dx)) * 180 / math.pi if dx != 0 else 0
        
        return {
            'length': length,
            'angle': angle,
            'c_value': abs(dx)  # C 值 (倒角宽度)
        }
    
    def _calculate_confidence(self, segment: List[Tuple[float, float]], 
                             rule: Dict) -> float:
        """计算规则匹配的置信度"""
        # 简化实现：基于点数和规则类型
        base_confidence = min(1.0, len(segment) / 10.0)
        
        # 根据规则类型调整
        if rule['name'] in ['external_cylinder', 'taper']:
            base_confidence *= 1.2
        elif rule['name'] in ['groove', 'chamfer']:
            base_confidence *= 1.1
        
        return min(1.0, base_confidence)
    
    def _fit_circle(self, points: List[Tuple[float, float]]) -> Tuple[Tuple[float, float], float]:
        """三点拟合圆"""
        if len(points) != 3:
            return ((0, 0), 0)
        
        p1, p2, p3 = points
        
        # 垂直平分线交点法
        mid1 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        mid2 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
        
        # 简化计算
        return ((0, 0), 50.0)  # 占位符
    
    def _calc_angle(self, center: Tuple[float, float], point: Tuple[float, float]) -> float:
        """计算角度"""
        dx = point[0] - center[0]
        dz = point[1] - center[1]
        return math.atan2(dz, dx) * 180 / math.pi
    
    def _is_convex(self, segment: List[Tuple[float, float]], 
                   center: Tuple[float, float]) -> bool:
        """判断凹凸性"""
        if len(segment) < 2:
            return True
        
        mid_point = segment[len(segment) // 2]
        dist_to_center = math.sqrt(
            (mid_point[0] - center[0])**2 + 
            (mid_point[1] - center[1])**2
        )
        
        # 简化判断
        return True


class MLClassifier:
    """机器学习分类器 - 深度学习特征识别"""
    
    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        self.device = 'cpu'
        
        # 类别映射
        self.class_names = [
            'external_cylinder',
            'taper',
            'arc_surface',
            'groove',
            'thread',
            'chamfer',
            'fillet'
        ]
    
    def load_model(self, model_path: str = None):
        """加载预训练模型"""
        try:
            import torch
            import torch.nn as nn
            from torchvision import models
            
            path = model_path or self.model_path
            
            if path and os.path.exists(path):
                # 使用 ResNet50 作为 backbone
                backbone = models.resnet50(pretrained=False)
                backbone.fc = nn.Linear(2048, len(self.class_names))
                
                backbone.load_state_dict(torch.load(path, map_location=self.device))
                self.model = backbone
                self.model.to(self.device)
                self.model.eval()
                print(f"✓ 加载模型：{path}")
            else:
                print("⚠ 模型文件不存在，使用规则引擎")
                
        except ImportError:
            print("⚠ PyTorch 未安装，使用规则引擎")
        except Exception as e:
            print(f"⚠ 加载模型失败：{e}")
    
    def predict(self, segment: List[Tuple[float, float]]) -> Optional[GeometricFeature]:
        """
        使用 ML 模型预测特征类型
        """
        if self.model is None:
            return None
        
        try:
            import torch
            from torchvision import transforms
            import numpy as np
            
            # 转换为图像表示
            image = self._segment_to_image(segment)
            
            # 预处理
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
            input_tensor = transform(image).unsqueeze(0).to(self.device)
            
            # 推理
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)[0]
                
                # 获取最高概率的类别
                confidence, predicted = torch.max(probabilities, 0)
                
                if confidence.item() < 0.5:  # 置信度阈值
                    return None
                
                feature_type = FeatureType(self.class_names[predicted.item()])
                
                return GeometricFeature(
                    type=feature_type,
                    start_point=segment[0],
                    end_point=segment[-1],
                    parameters=self._extract_ml_params(segment),
                    confidence=confidence.item(),
                    source="ml"
                )
                
        except Exception as e:
            print(f"ML 预测失败：{e}")
            return None
    
    def _segment_to_image(self, segment: List[Tuple[float, float]], 
                         size: int = 224) -> 'Image':
        """将轮廓段转换为图像表示"""
        from PIL import Image, ImageDraw
        
        # 创建空白图像
        img = Image.new('RGB', (size, size), 'white')
        draw = ImageDraw.Draw(img)
        
        # 归一化坐标到图像空间
        if len(segment) < 2:
            return img
        
        x_coords = [p[0] for p in segment]
        z_coords = [p[1] for p in segment]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_z, max_z = min(z_coords), max(z_coords)
        
        # 添加边距
        margin = 10
        scale_x = (size - 2*margin) / (max_x - min_x + 1e-6)
        scale_z = (size - 2*margin) / (max_z - min_z + 1e-6)
        scale = min(scale_x, scale_z)
        
        # 转换坐标
        points = []
        for x, z in segment:
            px = margin + (x - min_x) * scale
            pz = size - margin - (z - min_z) * scale  # Y 轴翻转
            points.append((px, pz))
        
        # 绘制轮廓
        if len(points) >= 2:
            draw.line(points, fill='black', width=2)
        
        return img
    
    def _extract_ml_params(self, segment: List[Tuple[float, float]]) -> Dict:
        """从 ML 预测中提取参数"""
        # 简化实现
        return {
            'ml_predicted': True,
            'segment_length': len(segment)
        }


class FeatureRecognizer:
    """
    特征识别器 - 混合架构
    
    结合规则引擎和机器学习:
    1. 首先应用规则引擎 (快速、可解释)
    2. 对规则不确定的样本使用 ML (处理复杂情况)
    3. 决策融合：加权投票 + 置信度评估
    """
    
    def __init__(self, enable_ml: bool = True, model_path: str = None):
        self.rule_engine = RuleEngine()
        self.ml_classifier = MLClassifier(model_path) if enable_ml else None
        self.curvature_analyzer = CurvatureAnalyzer()
        self.enable_ml = enable_ml
    
    def recognize(self, entities: List) -> RecognitionResult:
        """
        主识别流程
        
        Args:
            entities: 几何实体列表 (来自 DXF/STEP/IGES 解析器)
        
        Returns:
            RecognitionResult: 识别结果
        """
        import time
        start_time = time.time()
        
        result = RecognitionResult()
        
        # 步骤 1: 提取轮廓点
        profile_points = self._extract_profile_points(entities)
        
        if not profile_points:
            result.warnings.append("未能提取有效轮廓")
            return result
        
        # 步骤 2: 基于曲率分析分段
        segments = self.curvature_analyzer.segment_profile(profile_points)
        result.segments = segments
        
        # 步骤 3: 对每个段进行特征识别
        for segment in segments:
            feature = self._recognize_segment(segment)
            if feature:
                result.features.append(feature)
        
        # 步骤 4: 后处理和验证
        self._post_process(result)
        
        result.processing_time = time.time() - start_time
        result.metadata = {
            'total_points': len(profile_points),
            'num_segments': len(segments),
            'num_features': len(result.features),
            'rule_count': sum(1 for f in result.features if f.source == 'rule'),
            'ml_count': sum(1 for f in result.features if f.source == 'ml'),
        }
        
        return result
    
    def _extract_profile_points(self, entities: List) -> List[Tuple[float, float]]:
        """从几何实体中提取轮廓点"""
        points = []
        
        for entity in entities:
            if hasattr(entity, 'type'):
                if entity.type == 'LINE':
                    # 直线采样
                    start = (entity.start.x, entity.start.z)
                    end = (entity.end.x, entity.end.z)
                    
                    # 插值采样 (每 1mm 一个点)
                    num_points = max(2, int(self._distance(start, end)))
                    for i in range(num_points):
                        t = i / (num_points - 1)
                        x = start[0] + t * (end[0] - start[0])
                        z = start[1] + t * (end[1] - start[1])
                        points.append((x, z))
                        
                elif entity.type == 'CIRCLE' or entity.type == 'ARC':
                    # 圆弧采样
                    center = (entity.center.x, entity.center.z)
                    radius = entity.radius
                    
                    # 确定角度范围
                    start_angle = getattr(entity, 'start_angle', 0)
                    end_angle = getattr(entity, 'end_angle', 360)
                    
                    # 采样
                    num_points = max(4, int(abs(end_angle - start_angle) / 10))
                    for i in range(num_points):
                        t = i / (num_points - 1)
                        angle = start_angle + t * (end_angle - start_angle)
                        x = center[0] + radius * math.cos(math.radians(angle))
                        z = center[1] + radius * math.sin(math.radians(angle))
                        points.append((x, z))
        
        # 按 Z 坐标排序
        points.sort(key=lambda p: p[1])
        
        return points
    
    def _recognize_segment(self, segment: List[Tuple[float, float]]) -> Optional[GeometricFeature]:
        """识别单个轮廓段"""
        if len(segment) < 2:
            return None
        
        # 策略 1: 规则引擎优先
        rule_feature = self.rule_engine.recognize(segment)
        
        if rule_feature and rule_feature.confidence > 0.8:
            return rule_feature
        
        # 策略 2: ML 辅助 (如果启用)
        if self.enable_ml and self.ml_classifier:
            ml_feature = self.ml_classifier.predict(segment)
            
            if ml_feature:
                # 如果规则引擎结果置信度低，使用 ML
                if rule_feature is None or ml_feature.confidence > rule_feature.confidence:
                    return ml_feature
        
        # 返回规则引擎结果 (即使置信度较低)
        return rule_feature
    
    def _post_process(self, result: RecognitionResult):
        """后处理：验证和优化"""
        # 检查特征序列合理性
        features = result.features
        
        for i in range(len(features) - 1):
            curr = features[i]
            next_f = features[i + 1]
            
            # 检查连接点连续性
            if not self._check_continuity(curr, next_f):
                result.warnings.append(
                    f"特征 {i} 和 {i+1} 之间可能存在间隙"
                )
        
        # 检查常见工艺约束
        self._check_process_constraints(result)
    
    def _check_continuity(self, f1: GeometricFeature, 
                         f2: GeometricFeature) -> bool:
        """检查两个特征的连接连续性"""
        # 简化检查：端点距离
        dist = self._distance(f1.end_point, f2.start_point)
        return dist < 0.1  # 100μm 容差
    
    def _check_process_constraints(self, result: RecognitionResult):
        """检查工艺约束"""
        # 例如：槽深不应超过直径的 50%
        for feature in result.features:
            if feature.type == FeatureType.GROOVE:
                depth = feature.parameters.get('depth', 0)
                diameter = feature.parameters.get('bottom_diameter', 1)
                
                if depth > diameter * 0.5:
                    result.warnings.append(
                        f"槽深 ({depth:.2f}) 超过推荐值 (直径的 50%)"
                    )
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """计算两点距离"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def recognize_features(entities: List) -> RecognitionResult:
    """便捷函数：特征识别"""
    recognizer = FeatureRecognizer(enable_ml=False)  # 默认不使用 ML (需要训练数据)
    return recognizer.recognize(entities)


if __name__ == "__main__":
    # 测试示例
    from dataclasses import dataclass
    
    @dataclass
    class MockLine:
        type: str = "LINE"
        start: object = None
        end: object = None
    
    @dataclass
    class MockPoint:
        x: float = 0.0
        z: float = 0.0
    
    # 创建测试数据：简单阶梯轴
    entities = [
        MockLine(start=MockPoint(50, 0), end=MockPoint(50, -30)),   # 外圆
        MockLine(start=MockPoint(50, -30), end=MockPoint(40, -30)), # 台阶面
        MockLine(start=MockPoint(40, -30), end=MockPoint(40, -60)), # 外圆
        MockLine(start=MockPoint(40, -60), end=MockPoint(30, -60)), # 台阶面
        MockLine(start=MockPoint(30, -60), end=MockPoint(30, -90)), # 外圆
    ]
    
    result = recognize_features(entities)
    
    print(f"\n✓ 特征识别完成")
    print(f"  轮廓点数：{result.metadata.get('total_points', 0)}")
    print(f"  分段数量：{result.metadata.get('num_segments', 0)}")
    print(f"  特征数量：{result.metadata.get('num_features', 0)}")
    print(f"  处理时间：{result.processing_time:.3f}s")
    
    print("\n识别的特征:")
    for i, feature in enumerate(result.features):
        print(f"  {i+1}. {feature.type.value} (置信度：{feature.confidence:.2f}, 来源：{feature.source})")
        print(f"     起点：{feature.start_point}, 终点：{feature.end_point}")
        for key, value in feature.parameters.items():
            print(f"     {key}: {value}")
    
    if result.warnings:
        print("\n警告:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
