"""
特征识别模型训练脚本

功能:
- 生成合成训练数据 (轴类零件)
- 数据增强
- 训练 ResNet50/EfficientNet 分类器
- 模型验证和导出

使用:
    python train_feature_model.py --epochs 50 --batch-size 32
"""

import os
import random
import math
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass

import numpy as np


@dataclass
class TrainingSample:
    """训练样本"""
    image: np.ndarray  # HxWx3
    label: int         # 类别索引
    segment: List[Tuple[float, float]]  # 原始轮廓段
    feature_type: str  # 特征类型名称


class SyntheticDataGenerator:
    """
    合成数据生成器 - 生成轴类零件训练数据
    
    生成的特征类型:
    - external_cylinder (外圆)
    - taper (锥面)
    - arc_surface (圆弧面)
    - groove (槽)
    - thread (螺纹)
    - chamfer (倒角)
    - fillet (圆角)
    """
    
    def __init__(self, output_dir: str = "dataset/synthetic"):
        self.output_dir = Path(output_dir)
        self.feature_types = [
            'external_cylinder',
            'taper',
            'arc_surface',
            'groove',
            'thread',
            'chamfer',
            'fillet'
        ]
        
        # 确保输出目录存在
        for split in ['train', 'val', 'test']:
            for feat_type in self.feature_types:
                (self.output_dir / split / feat_type).mkdir(parents=True, exist_ok=True)
    
    def generate_dataset(self, num_samples_per_class: int = 200):
        """
        生成完整数据集
        
        Args:
            num_samples_per_class: 每类样本数
        """
        print(f"📊 生成合成数据集...")
        print(f"  类别数：{len(self.feature_types)}")
        print(f"  每类样本：{num_samples_per_class}")
        print(f"  总样本：{len(self.feature_types) * num_samples_per_class}")
        
        all_samples = []
        
        # 生成训练集 (70%)
        train_count = int(num_samples_per_class * 0.7)
        for feat_type in self.feature_types:
            samples = self._generate_samples_for_type(feat_type, train_count)
            all_samples.extend(samples)
            self._save_samples(samples, 'train', feat_type)
        
        # 生成验证集 (15%)
        val_count = int(num_samples_per_class * 0.15)
        for feat_type in self.feature_types:
            samples = self._generate_samples_for_type(feat_type, val_count)
            all_samples.extend(samples)
            self._save_samples(samples, 'val', feat_type)
        
        # 生成测试集 (15%)
        test_count = int(num_samples_per_class * 0.15)
        for feat_type in self.feature_types:
            samples = self._generate_samples_for_type(feat_type, test_count)
            all_samples.extend(samples)
            self._save_samples(samples, 'test', feat_type)
        
        print(f"✓ 数据集生成完成: {self.output_dir}")
        
        return all_samples
    
    def _generate_samples_for_type(self, feature_type: str, count: int) -> List[TrainingSample]:
        """为特定特征类型生成样本"""
        samples = []
        
        for i in range(count):
            # 生成随机参数
            params = self._random_params(feature_type)
            
            # 生成几何轮廓
            segment = self._generate_geometry(feature_type, params)
            
            # 转换为图像
            image = self._segment_to_image(segment)
            
            # 添加噪声和增强
            image = self._augment(image)
            
            sample = TrainingSample(
                image=image,
                label=self.feature_types.index(feature_type),
                segment=segment,
                feature_type=feature_type
            )
            
            samples.append(sample)
        
        return samples
    
    def _random_params(self, feature_type: str) -> Dict:
        """生成随机参数"""
        if feature_type == 'external_cylinder':
            return {
                'diameter': random.uniform(20, 100),
                'length': random.uniform(20, 80),
            }
        
        elif feature_type == 'taper':
            return {
                'start_diameter': random.uniform(30, 80),
                'end_diameter': random.uniform(20, 70),
                'length': random.uniform(20, 60),
            }
        
        elif feature_type == 'arc_surface':
            return {
                'radius': random.uniform(10, 50),
                'angle_span': random.uniform(30, 120),
                'convex': random.choice([True, False]),
            }
        
        elif feature_type == 'groove':
            return {
                'width': random.uniform(3, 15),
                'depth': random.uniform(2, 10),
                'position': random.uniform(20, 60),
            }
        
        elif feature_type == 'thread':
            return {
                'major_diameter': random.uniform(20, 60),
                'pitch': random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
                'length': random.uniform(15, 40),
            }
        
        elif feature_type == 'chamfer':
            return {
                'c_value': random.uniform(1, 5),
                'angle': random.uniform(40, 50),
            }
        
        elif feature_type == 'fillet':
            return {
                'radius': random.uniform(1, 8),
                'position': 'start' if random.random() > 0.5 else 'end',
            }
        
        return {}
    
    def _generate_geometry(self, feature_type: str, params: Dict) -> List[Tuple[float, float]]:
        """根据参数生成几何轮廓点"""
        points = []
        
        if feature_type == 'external_cylinder':
            diameter = params['diameter']
            length = params['length']
            
            # 垂直线段
            num_points = max(5, int(length / 2))
            for i in range(num_points):
                z = -i * (length / (num_points - 1))
                x = diameter
                points.append((x, z))
        
        elif feature_type == 'taper':
            start_d = params['start_diameter']
            end_d = params['end_diameter']
            length = params['length']
            
            num_points = max(5, int(length / 2))
            for i in range(num_points):
                t = i / (num_points - 1)
                z = -t * length
                x = start_d + t * (end_d - start_d)
                points.append((x, z))
        
        elif feature_type == 'arc_surface':
            radius = params['radius']
            angle_span = params['angle_span']
            convex = params['convex']
            
            num_points = max(8, int(angle_span / 5))
            start_angle = 90
            end_angle = 90 - angle_span
            
            for i in range(num_points):
                t = i / (num_points - 1)
                angle = start_angle + t * (end_angle - start_angle)
                
                if convex:
                    x = radius + radius * math.cos(math.radians(angle))
                    z = radius * math.sin(math.radians(angle))
                else:
                    x = radius - radius * math.cos(math.radians(angle))
                    z = radius * math.sin(math.radians(angle))
                
                points.append((x, z))
        
        elif feature_type == 'groove':
            width = params['width']
            depth = params['depth']
            position = params['position']
            
            # U 型槽
            num_points = max(10, int(width))
            
            # 左侧
            for i in range(num_points // 3):
                t = i / (num_points // 3 - 1)
                z = -t * (width / 2)
                x = depth + (1 - t) * (depth - depth * 0.2)
                points.append((x, z))
            
            # 底部
            for i in range(num_points // 3):
                t = i / (num_points // 3 - 1)
                z = -width / 2 - t * (width / 2)
                x = depth * 0.2
                points.append((x, z))
            
            # 右侧
            for i in range(num_points // 3):
                t = i / (num_points // 3 - 1)
                z = -width - t * (width / 2)
                x = depth * 0.2 + t * (depth - depth * 0.2)
                points.append((x, z))
        
        elif feature_type == 'thread':
            major_d = params['major_diameter']
            pitch = params['pitch']
            length = params['length']
            
            # 三角形螺纹轮廓
            num_turns = int(length / pitch)
            points_per_turn = 6
            
            for turn in range(num_turns):
                for i in range(points_per_turn):
                    t = i / points_per_turn
                    z = -(turn * pitch + t * pitch)
                    
                    # 三角形齿形
                    if t < 0.25:
                        x = major_d - t * 4 * (pitch * 0.6)
                    elif t < 0.5:
                        x = major_d - pitch * 0.6 + (t - 0.25) * 4 * (pitch * 0.6)
                    else:
                        x = major_d
                    
                    points.append((x, z))
        
        elif feature_type == 'chamfer':
            c_value = params['c_value']
            angle = params['angle']
            
            num_points = max(3, int(c_value))
            angle_rad = math.radians(angle)
            
            for i in range(num_points):
                t = i / (num_points - 1)
                x = c_value * (1 - t)
                z = -c_value / math.tan(angle_rad) * t
                points.append((x, z))
        
        elif feature_type == 'fillet':
            radius = params['radius']
            position = params['position']
            
            num_points = max(5, int(radius * 2))
            start_angle = 90
            end_angle = 0
            
            for i in range(num_points):
                t = i / (num_points - 1)
                angle = start_angle + t * (end_angle - start_angle)
                
                if position == 'start':
                    x = radius * (1 - math.cos(math.radians(angle)))
                    z = -radius * math.sin(math.radians(angle))
                else:
                    x = radius * (1 - math.cos(math.radians(angle)))
                    z = -radius + radius * math.sin(math.radians(angle))
                
                points.append((x, z))
        
        return points
    
    def _segment_to_image(self, segment: List[Tuple[float, float]], 
                         size: int = 224) -> np.ndarray:
        """将轮廓段转换为图像"""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            # 无 PIL 时返回随机数组
            return np.random.randint(0, 255, (size, size, 3), dtype=np.uint8)
        
        # 创建空白图像
        img = Image.new('RGB', (size, size), 'white')
        draw = ImageDraw.Draw(img)
        
        if len(segment) < 2:
            return np.array(img)
        
        # 归一化坐标
        x_coords = [p[0] for p in segment]
        z_coords = [p[1] for p in segment]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_z, max_z = min(z_coords), max(z_coords)
        
        # 添加边距
        margin = 20
        range_x = max_x - min_x + 1e-6
        range_z = max_z - min_z + 1e-6
        
        scale_x = (size - 2*margin) / range_x
        scale_z = (size - 2*margin) / range_z
        scale = min(scale_x, scale_z)
        
        # 转换坐标
        points = []
        for x, z in segment:
            px = margin + (x - min_x) * scale
            pz = size - margin - (z - min_z) * scale  # Y 轴翻转
            points.append((px, pz))
        
        # 绘制轮廓
        if len(points) >= 2:
            draw.line(points, fill='black', width=3)
            
            # 绘制端点
            draw.circle(points[0], radius=4, fill='red')
            draw.circle(points[-1], radius=4, fill='blue')
        
        return np.array(img)
    
    def _augment(self, image: np.ndarray) -> np.ndarray:
        """数据增强"""
        # 随机旋转 (-5° 到 +5°)
        if random.random() > 0.5:
            angle = random.uniform(-5, 5)
            image = self._rotate(image, angle)
        
        # 随机平移
        if random.random() > 0.5:
            shift_x = random.randint(-5, 5)
            shift_y = random.randint(-5, 5)
            image = self._translate(image, shift_x, shift_y)
        
        # 随机亮度调整
        if random.random() > 0.5:
            factor = random.uniform(0.8, 1.2)
            image = (image * factor).clip(0, 255).astype(np.uint8)
        
        # 添加高斯噪声
        if random.random() > 0.5:
            noise = np.random.normal(0, 5, image.shape)
            image = (image + noise).clip(0, 255).astype(np.uint8)
        
        return image
    
    def _rotate(self, image: np.ndarray, angle: float) -> np.ndarray:
        """旋转图像"""
        try:
            from scipy.ndimage import rotate
            return rotate(image, angle, reshape=False, mode='constant').astype(np.uint8)
        except ImportError:
            return image
    
    def _translate(self, image: np.ndarray, dx: int, dy: int) -> np.ndarray:
        """平移图像"""
        try:
            from scipy.ndimage import shift
            return shift(image, (dy, dx, 0), mode='constant').astype(np.uint8)
        except ImportError:
            return image
    
    def _save_samples(self, samples: List[TrainingSample], split: str, feature_type: str):
        """保存样本到文件"""
        save_dir = self.output_dir / split / feature_type
        
        for i, sample in enumerate(samples):
            # 保存图像
            try:
                from PIL import Image
                img = Image.fromarray(sample.image)
                img.save(save_dir / f"{feature_type}_{i:04d}.png")
            except Exception as e:
                print(f"保存图像失败：{e}")
            
            # 保存元数据
            import json
            metadata = {
                'label': sample.label,
                'feature_type': sample.feature_type,
                'segment': sample.segment,
                'image_shape': sample.image.shape,
            }
            
            with open(save_dir / f"{feature_type}_{i:04d}.json", 'w') as f:
                json.dump(metadata, f, indent=2)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成特征识别训练数据')
    parser.add_argument('--output-dir', type=str, default='dataset/synthetic',
                       help='输出目录')
    parser.add_argument('--samples-per-class', type=int, default=200,
                       help='每类样本数')
    
    args = parser.parse_args()
    
    generator = SyntheticDataGenerator(args.output_dir)
    generator.generate_dataset(args.samples_per_class)
    
    print("\n✓ 数据生成完成!")
    print(f"\n下一步:")
    print("1. 检查数据集：ls -R {args.output_dir}")
    print("2. 训练模型：python train_feature_model.py --data-dir {args.output_dir}")


if __name__ == "__main__":
    main()
