#!/usr/bin/env python3
"""
迁移脚本: 从硬性开关的Task-Aware Config迁移到软性权重的Adaptive Config

核心修改:
1. 替换import和初始化
2. 将 enable_X 检查改为权重阈值检查
3. 添加权重使用逻辑
"""

import re
import sys

def migrate_brain_coordinator():
    """迁移brain_coordinator_refactored.py"""
    file_path = "src/coordination/brain_coordinator_refactored.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. 替换import
    content = content.replace(
        "from .dataset_aware_config import get_dataset_config_manager",
        "from .adaptive_config import get_adaptive_config_manager"
    )

    # 2. 替换初始化
    content = content.replace(
        "self.dataset_config_manager = get_dataset_config_manager()",
        "self.adaptive_config_manager = get_adaptive_config_manager()"
    )
    content = content.replace(
        'logger.debug("  ✅ DatasetAwareConfigManager initialized")',
        'logger.debug("  ✅ AdaptiveConfigManager initialized")'
    )

    # 3. 替换配置获取调用 - 改为get_adaptive_weights
    # dataset_config = self.dataset_config_manager.apply_config(context)
    # → adaptive_weights = self.adaptive_config_manager.get_adaptive_weights(query, context)

    # 先替换变量名
    content = content.replace(
        "dataset_config = self.dataset_config_manager.apply_config(",
        "adaptive_weights = self.adaptive_config_manager.get_adaptive_weights(context.get('user_input', ''),"
    )

    # 4. 替换硬性开关检查为权重检查
    # dataset_config.enable_preference_extraction → adaptive_weights.preference_extraction_weight > 0.3
    content = content.replace(
        "dataset_config.enable_preference_extraction",
        "adaptive_weights.preference_extraction_weight > 0.3"
    )

    # dataset_config.enable_preference_aware_retrieval → adaptive_weights.preference_retrieval_boost > 0.1
    content = content.replace(
        "dataset_config.enable_preference_aware_retrieval",
        "adaptive_weights.preference_retrieval_boost > 0.1"
    )

    # 5. 替换日志调用
    content = content.replace(
        "self.dataset_config_manager.get_config_summary()",
        "self.adaptive_config_manager.get_config_summary()"
    )

    # 6. 检查是否有修改
    if content == original_content:
        print("❌ 没有检测到任何修改！")
        return False

    # 7. 备份并写入
    backup_path = file_path + ".backup_adaptive"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"✅ 原文件已备份到: {backup_path}")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 已更新: {file_path}")

    # 8. 统计修改
    changes = []
    if "adaptive_config" in content and "dataset_aware_config" not in content:
        changes.append("Import替换")
    if "adaptive_config_manager" in content:
        changes.append("Manager替换")
    if "adaptive_weights.preference_extraction_weight" in content:
        changes.append("偏好提取权重检查")
    if "adaptive_weights.preference_retrieval_boost" in content:
        changes.append("偏好检索权重检查")

    print(f"\n📊 完成修改: {', '.join(changes)}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("迁移到Adaptive Config (软性权重方案)")
    print("=" * 60)
    print()

    success = migrate_brain_coordinator()

    if success:
        print("\n✅ 迁移成功！")
        print("\n下一步: 运行测试验证通用性")
    else:
        print("\n❌ 迁移失败")
        sys.exit(1)
