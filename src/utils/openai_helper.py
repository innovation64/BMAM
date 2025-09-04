#!/usr/bin/env python3
"""
OpenAI API 辅助函数
为实验代码提供统一的 API 客户端
"""

import os
from openai import AsyncOpenAI, OpenAI
from typing import Optional, Union, Dict, Any


def get_api_client(async_client: bool = True) -> Union[AsyncOpenAI, OpenAI]:
    """
    获取 OpenAI API 客户端
    
    Args:
        async_client: 是否返回异步客户端
        
    Returns:
        OpenAI 客户端实例
    """
    # 从环境变量或 .env 文件加载 API 密钥
    api_key = load_api_key()
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY environment variable "
            "or create a .env file with OPENAI_API_KEY=your-key-here"
        )
    
    # 获取基础 URL（如果使用代理）
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    if async_client:
        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
    else:
        return OpenAI(
            api_key=api_key,
            base_url=base_url
        )


def load_api_key() -> Optional[str]:
    """
    加载 OpenAI API 密钥
    
    Returns:
        API 密钥字符串，如果未找到则返回 None
    """
    # 方法 1: 从环境变量
    api_key = os.getenv('OPENAI_API_KEY')
    
    # 方法 2: 从 .env 文件
    if not api_key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('OPENAI_API_KEY='):
                        api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
    
    # 方法 3: 从用户主目录的 .env 文件
    if not api_key:
        home_env_path = os.path.join(os.path.expanduser('~'), '.env')
        if os.path.exists(home_env_path):
            with open(home_env_path, 'r') as f:
                for line in f:
                    if line.startswith('OPENAI_API_KEY='):
                        api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
    
    # 设置环境变量（供其他组件使用）
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
    
    return api_key


def check_api_key() -> bool:
    """
    检查 API 密钥是否已配置
    
    Returns:
        如果 API 密钥已配置返回 True，否则返回 False
    """
    api_key = load_api_key()
    return bool(api_key)


def get_model_pricing(model: str) -> Dict[str, float]:
    """
    获取模型定价信息
    
    Args:
        model: 模型名称
        
    Returns:
        包含输入和输出价格的字典（每1K tokens）
    """
    pricing = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    
    return pricing.get(model, {"input": 0.001, "output": 0.002})


# 为了兼容性，导出一个简单的 get_api_client 函数

def get_api_client_simple() -> AsyncOpenAI:
    """简化的 API 客户端获取函数（用于向后兼容）"""
    return get_api_client(async_client=True)


# 直接导出主函数，不再使用别名
# get_api_client 函数已在上面定义