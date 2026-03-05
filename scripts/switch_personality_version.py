#!/usr/bin/env python3
"""
快速切换PersonalityAgent版本的脚本
Usage:
    python scripts/switch_personality_version.py [original|mbti]
    python scripts/switch_personality_version.py info
    python scripts/switch_personality_version.py mbti INTJ  # 设置MBTI类型
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.coordination.personality_version_manager import get_version_manager


def print_current_info():
    """打印当前版本信息"""
    manager = get_version_manager()
    info = manager.get_version_info()

    print("=" * 60)
    print("PersonalityAgent 版本信息")
    print("=" * 60)
    print(f"当前版本: {info['current']}")
    print(f"\n版本详情:")

    current_details = info['current_details']
    print(f"  名称: {current_details.get('name', 'N/A')}")
    print(f"  描述: {current_details.get('description', 'N/A')}")
    print(f"  特性:")
    for feature in current_details.get('features', []):
        print(f"    - {feature}")

    # 如果是MBTI版本，显示当前人格类型
    if info['current'] == 'mbti':
        mbti_config_path = project_root / "config" / "mbti_personality.json"
        if mbti_config_path.exists():
            with open(mbti_config_path, 'r', encoding='utf-8') as f:
                mbti_config = json.load(f)
            print(f"\n当前MBTI人格类型: {mbti_config.get('current_personality', 'N/A')}")

    print(f"\n实验追踪: {'启用' if info['experiment_enabled'] else '禁用'}")

    print("\n可用版本:")
    for version_key, version_info in info['available_versions'].items():
        marker = "✓" if version_key == info['current'] else " "
        print(f"  [{marker}] {version_key}: {version_info.get('name', 'N/A')}")

    print("=" * 60)


def switch_version(target_version: str):
    """切换到指定版本"""
    manager = get_version_manager()

    print(f"正在切换到 {target_version} 版本...")
    success, message = manager.set_version(target_version)

    if success:
        print(f"✓ {message}")
        print("\n⚠️  请重启系统以应用更改")
    else:
        print(f"✗ {message}")
        return 1

    return 0


def set_mbti_type(mbti_type: str):
    """设置MBTI人格类型"""
    valid_types = [
        'INTJ', 'INTP', 'ENTJ', 'ENTP',
        'INFJ', 'INFP', 'ENFJ', 'ENFP',
        'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
        'ISTP', 'ISFP', 'ESTP', 'ESFP'
    ]

    mbti_type = mbti_type.upper()
    if mbti_type not in valid_types:
        print(f"✗ 无效的MBTI类型: {mbti_type}")
        print(f"有效类型: {', '.join(valid_types)}")
        return 1

    mbti_config_path = project_root / "config" / "mbti_personality.json"

    try:
        # 读取配置
        if mbti_config_path.exists():
            with open(mbti_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            print("✗ MBTI配置文件不存在")
            return 1

        # 更新类型
        old_type = config.get('current_personality', 'ENFP')
        config['current_personality'] = mbti_type

        # 保存配置
        with open(mbti_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"✓ MBTI人格类型已更新: {old_type} → {mbti_type}")
        print("\n⚠️  请重启系统以应用更改")
        return 0

    except Exception as e:
        print(f"✗ 设置失败: {e}")
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/switch_personality_version.py info")
        print("  python scripts/switch_personality_version.py [original|mbti]")
        print("  python scripts/switch_personality_version.py mbti INTJ")
        return 1

    command = sys.argv[1].lower()

    if command == 'info':
        print_current_info()
        return 0

    elif command in ['original', 'mbti']:
        # 如果是mbti且提供了第二个参数，设置MBTI类型
        if command == 'mbti' and len(sys.argv) >= 3:
            mbti_type = sys.argv[2]
            # 先切换到mbti版本
            exit_code = switch_version('mbti')
            if exit_code != 0:
                return exit_code
            # 再设置MBTI类型
            return set_mbti_type(mbti_type)
        else:
            return switch_version(command)

    else:
        print(f"✗ 未知命令: {command}")
        print("有效命令: info, original, mbti")
        return 1


if __name__ == "__main__":
    sys.exit(main())