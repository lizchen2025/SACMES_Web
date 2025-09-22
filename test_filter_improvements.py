#!/usr/bin/env python3
"""
测试滤波器改进的脚本
"""

import numpy as np
from data_processing.swv_analyzer import analyze_swv_data

def test_new_filter_modes():
    """测试新的滤波器模式"""

    # 模拟分析参数
    test_params = {
        'voltage_column': 1,
        'current_column': 2,
        'spacing_index': 1,
        'num_electrodes': 1,
        'delimiter': 1,
        'file_extension': '.txt',
        'SelectedOptions': 'Peak Height Extraction',
        'xAxisOptions': 'Experiment Time',  # 测试时间单位
        'sampleRate': 120,  # 2分钟一个文件
    }

    # 测试用例1：Hampel禁用，SG自动
    print("=== 测试用例1：Hampel禁用，SG自动 ===")
    params1 = test_params.copy()
    params1.update({
        'hampel_mode': 'disabled',
        'sg_mode': 'auto'
    })
    print(f"滤波器配置: Hampel={params1['hampel_mode']}, SG={params1['sg_mode']}")

    # 测试用例2：Hampel自动，SG禁用
    print("\n=== 测试用例2：Hampel自动，SG禁用 ===")
    params2 = test_params.copy()
    params2.update({
        'hampel_mode': 'auto',
        'sg_mode': 'disabled'
    })
    print(f"滤波器配置: Hampel={params2['hampel_mode']}, SG={params2['sg_mode']}")

    # 测试用例3：两个都手动
    print("\n=== 测试用例3：两个都手动 ===")
    params3 = test_params.copy()
    params3.update({
        'hampel_mode': 'manual',
        'sg_mode': 'manual',
        'hampel_window': 7,
        'hampel_threshold': 2.5,
        'sg_window': 11,
        'sg_degree': 3
    })
    print(f"滤波器配置: Hampel={params3['hampel_mode']}, SG={params3['sg_mode']}")
    print(f"手动参数: Hampel窗口={params3['hampel_window']}, SG窗口={params3['sg_window']}")

    # 测试用例4：两个都禁用
    print("\n=== 测试用例4：两个都禁用 ===")
    params4 = test_params.copy()
    params4.update({
        'hampel_mode': 'disabled',
        'sg_mode': 'disabled'
    })
    print(f"滤波器配置: Hampel={params4['hampel_mode']}, SG={params4['sg_mode']}")

    print("\n滤波器模式测试完成！")
    print("注意: 实际文件处理需要有效的数据文件。")

def test_time_axis_conversion():
    """测试时间轴换算"""
    from app import calculate_trends

    print("\n=== 测试时间轴换算（分钟单位）===")

    # 模拟数据
    raw_peaks = {
        'averaged': {
            '50': {'1': 1.0, '2': 1.1, '3': 1.2, '4': 1.3, '5': 1.4}
        }
    }

    params = {
        'num_files': 5,
        'frequencies': [50],
        'normalizationPoint': 1,
        'xAxisOptions': 'Experiment Time',
        'sampleRate': 120  # 2分钟一个文件
    }

    result = calculate_trends(raw_peaks, params)

    print(f"原始sampleRate: {params['sampleRate']}秒")
    print(f"X轴时间值（分钟）: {result['x_axis_values']}")
    print("预期: [0.0, 2.0, 4.0, 6.0, 8.0] (每2分钟一个点)")

    # 验证计算是否正确
    expected = [i * 120 / 60 for i in range(5)]  # 每个文件120秒，转换为分钟
    if result['x_axis_values'] == expected:
        print("✓ 时间轴换算正确")
    else:
        print("✗ 时间轴换算有误")

if __name__ == "__main__":
    print("=== SACMES 滤波器改进测试 ===")

    test_new_filter_modes()
    test_time_axis_conversion()

    print("\n所有测试完成！")