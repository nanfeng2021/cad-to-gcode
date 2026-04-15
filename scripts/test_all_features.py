"""
CAD to G-code Platform - 功能集成测试

测试所有核心功能:
1. 特征识别
2. 刀路仿真
3. API 端点
4. G 代码生成

运行:
    python scripts/test_all_features.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_feature_recognition():
    """测试特征识别功能"""
    print("\n" + "="*60)
    print("🧠 测试特征识别系统")
    print("="*60)
    
    from src.ai.feature_recognition import FeatureRecognizer, GeometricFeature, FeatureType
    
    # 创建模拟数据
    from dataclasses import dataclass
    
    @dataclass
    class MockPoint:
        x: float
        z: float
    
    @dataclass
    class MockLine:
        type: str = "LINE"
        start: object = None
        end: object = None
    
    # 测试用例 1: 简单阶梯轴
    print("\n测试 1: 简单阶梯轴")
    entities = [
        MockLine(start=MockPoint(50, 0), end=MockPoint(50, -30)),
        MockLine(start=MockPoint(50, -30), end=MockPoint(40, -30)),
        MockLine(start=MockPoint(40, -30), end=MockPoint(40, -60)),
        MockLine(start=MockPoint(40, -60), end=MockPoint(30, -60)),
        MockLine(start=MockPoint(30, -60), end=MockPoint(30, -90)),
    ]
    
    recognizer = FeatureRecognizer(enable_ml=False)
    result = recognizer.recognize(entities)
    
    print(f"  ✓ 轮廓点数：{len(result.segments[0]) if result.segments else 0}")
    print(f"  ✓ 识别特征数：{len(result.features)}")
    print(f"  ✓ 处理时间：{result.processing_time:.3f}s")
    
    for i, feat in enumerate(result.features):
        print(f"    {i+1}. {feat.type.value} (置信度：{feat.confidence:.2f})")
    
    assert len(result.features) > 0, "未识别到任何特征"
    print("  ✅ 测试通过")
    
    return True


def test_toolpath_simulation():
    """测试刀路仿真功能"""
    print("\n" + "="*60)
    print("🎬 测试刀路轨迹仿真")
    print("="*60)
    
    from src.cam.toolpath_simulation import ToolpathSimulator
    
    # 测试 G 代码
    test_gcode = """
    O1000
    G54 G00 X100 Z5
    S1000 M03
    G00 X50 Z0
    G01 X50 Z-30 F200
    G01 X45 Z-30
    G01 X45 Z-60
    G01 X40 Z-60
    G01 X40 Z-90
    G00 X100 Z5
    M30
    """
    
    simulator = ToolpathSimulator()
    result = simulator.simulate(test_gcode)
    
    print(f"\n  ✓ 程序段数：{len(result.toolpath)}")
    print(f"  ✓ 总加工时间：{result.total_time:.2f}s")
    print(f"  ✓ 总路径长度：{result.total_distance:.2f}mm")
    print(f"  ✓ 切削距离：{result.cutting_distance:.2f}mm")
    print(f"  ✓ 碰撞警告：{len(result.collisions)}")
    
    if result.bounding_box:
        bbox = result.bounding_box
        print(f"  ✓ 包围盒：X[{bbox['min_x']:.1f}, {bbox['max_x']:.1f}], "
              f"Z[{bbox['min_z']:.1f}, {bbox['max_z']:.1f}]")
    
    assert len(result.toolpath) > 0, "未生成刀路段"
    assert result.total_time > 0, "加工时间为 0"
    print("  ✅ 测试通过")
    
    return True


def test_gcode_generation():
    """测试 G 代码生成功能"""
    print("\n" + "="*60)
    print("⚙️  测试 G 代码生成")
    print("="*60)
    
    from src.core.process_planning import CuttingRulesEngine
    from src.cam.gcode_generator import GCodeGenerator
    
    # 测试切削参数
    engine = CuttingRulesEngine()
    params = engine.get_params("45#钢", "粗车")
    
    print(f"\n  切削参数测试:")
    print(f"    材料：45#钢")
    print(f"    工序：粗车")
    print(f"    主轴转速：{params.spindle_speed} rpm")
    print(f"    进给速度：{params.feed_rate} mm/rev")
    print(f"    切深：{params.depth_of_cut} mm")
    
    # 测试 G 代码生成
    generator = GCodeGenerator(machine_system="FANUC")
    generator.generate_header(program_name="O1000", part_name="TEST_PART")
    
    generator._add_block("G21", "Metric units")
    generator._add_block("G00 X50 Z5", "Rapid to start")
    generator._add_block("G01 Z-30 F0.2", "Linear cut")
    generator._add_block("G00 X100 Z100", "Retract")
    generator.generate_footer()
    
    gcode = generator.get_gcode()
    lines = gcode.split('\n')
    
    print(f"\n  生成的 G 代码:")
    print(f"    行数：{len(lines)}")
    print(f"    前 5 行:")
    for line in lines[:5]:
        print(f"      {line}")
    
    assert len(gcode) > 0, "G 代码为空"
    assert "O1000" in gcode, "缺少程序号"
    print("  ✅ 测试通过")
    
    return True


def test_api_health():
    """测试 API 健康检查"""
    print("\n" + "="*60)
    print("🌐 测试 API 端点")
    print("="*60)
    
    import subprocess
    import time
    import requests
    
    print("\n  启动测试服务器...")
    
    # 启动 FastAPI (后台)
    proc = subprocess.Popen(
        ["uvicorn", "src.web.api:app", "--port", "8765"],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待服务器启动
    time.sleep(3)
    
    try:
        # 测试健康检查
        response = requests.get("http://localhost:8765/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ 状态：{data.get('status')}")
            print(f"  ✓ 版本：{data.get('version')}")
            print(f"  ✓ 材料数：{data.get('materials_count')}")
            print(f"  ✓ 程序数：{data.get('programs_count')}")
            assert data['status'] == 'healthy'
            print("  ✅ 测试通过")
        else:
            print(f"  ❌ 失败：HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ 错误：{e}")
        return False
    finally:
        # 关闭服务器
        proc.terminate()
        proc.wait()
        print("  测试服务器已关闭")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print(" CAD to G-code Platform - 功能集成测试")
    print("🚀"*30)
    
    tests = [
        ("特征识别", test_feature_recognition),
        ("刀路仿真", test_toolpath_simulation),
        ("G 代码生成", test_gcode_generation),
        ("API 端点", test_api_health),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"  ❌ 测试失败：{e}")
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        icon = "✅" if success else "❌"
        print(f"{icon} {name}: {'通过' if success else '失败'}")
        if error:
            print(f"   错误：{error}")
    
    print("\n" + "-"*60)
    print(f"总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
