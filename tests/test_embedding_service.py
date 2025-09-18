#!/usr/bin/env python3
"""
Unit tests for OpenAI Embedding Service
测试OpenAI嵌入服务的所有功能
"""

import asyncio
import tempfile
import shutil
import numpy as np
from pathlib import Path
import json
from unittest.mock import AsyncMock, patch
import pytest

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.openai_embedding_service import OpenAIEmbeddingService, EmbeddingCache


class TestEmbeddingCache:
    """EmbeddingCache单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.cache = EmbeddingCache(cache_dir=self.test_dir, max_size=10, ttl_hours=1)
    
    def teardown_method(self):
        """清理测试环境"""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        text1 = "Hello world"
        text2 = "Hello world"
        text3 = "Different text"
        
        key1 = self.cache._get_cache_key(text1)
        key2 = self.cache._get_cache_key(text2)
        key3 = self.cache._get_cache_key(text3)
        
        assert key1 == key2  # 相同文本应该产生相同键
        assert key1 != key3  # 不同文本应该产生不同键
        
        print("✅ 缓存键生成测试通过")
    
    def test_cache_put_and_get(self):
        """测试缓存存储和获取"""
        text = "test text for caching"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # 存储到缓存
        self.cache.put(text, embedding)
        
        # 从缓存获取
        cached_embedding = self.cache.get(text)
        
        assert cached_embedding is not None
        assert cached_embedding == embedding
        
        # 测试不存在的文本
        non_cached = self.cache.get("non-existent text")
        assert non_cached is None
        
        print("✅ 缓存存储和获取测试通过")
    
    def test_cache_persistence(self):
        """测试缓存持久化"""
        text = "persistent test text"
        embedding = [0.9, 0.8, 0.7, 0.6]
        
        # 存储到缓存
        self.cache.put(text, embedding)
        
        # 创建新的缓存实例（模拟重启）
        new_cache = EmbeddingCache(cache_dir=self.test_dir, max_size=10, ttl_hours=1)
        
        # 应该能够从持久化文件中加载
        cached_embedding = new_cache.get(text)
        assert cached_embedding == embedding
        
        print("✅ 缓存持久化测试通过")
    
    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        # 填满缓存
        for i in range(15):  # 超过max_size=10
            text = f"text_{i}"
            embedding = [float(i)] * 5
            self.cache.put(text, embedding)
        
        # 缓存中应该只有最新的10个
        cache_size = len(self.cache._cache)
        assert cache_size == 10
        
        # 最早的项目应该被移除
        oldest_cached = self.cache.get("text_0")
        assert oldest_cached is None
        
        # 最新的项目应该存在
        newest_cached = self.cache.get("text_14")
        assert newest_cached is not None
        
        print("✅ 缓存大小限制测试通过")
    
    async def test_get_embedding_with_cache(self):
        """测试带缓存的嵌入获取"""
        text = "test embedding with cache"
        expected_embedding = np.array([0.1, 0.2, 0.3])
        
        # Mock compute function
        async def mock_compute_func(input_text):
            return expected_embedding
        
        # 第一次调用应该计算并缓存
        result1 = await self.cache.get_embedding(text, mock_compute_func)
        np.testing.assert_array_equal(result1, expected_embedding)
        
        # 第二次调用应该从缓存获取
        result2 = await self.cache.get_embedding(text, mock_compute_func)
        np.testing.assert_array_equal(result2, expected_embedding)
        
        # 验证缓存中确实存在
        cached = self.cache.get(text)
        assert cached is not None
        
        print("✅ 带缓存的嵌入获取测试通过")
    
    async def test_get_batch_embeddings_with_cache(self):
        """测试批量嵌入的缓存功能"""
        texts = ["text1", "text2", "text3", "text4"]
        
        # 预先缓存一些文本
        self.cache.put("text1", [0.1, 0.2])
        self.cache.put("text3", [0.5, 0.6])
        
        # Mock batch compute function
        async def mock_batch_compute_func(uncached_texts):
            # 应该只包含未缓存的文本
            expected_uncached = ["text2", "text4"]
            assert set(uncached_texts) == set(expected_uncached)
            
            return [np.array([0.3, 0.4]), np.array([0.7, 0.8])]
        
        # 执行批量获取
        results = await self.cache.get_batch_embeddings(texts, mock_batch_compute_func)
        
        # 验证所有结果
        assert len(results) == 4
        np.testing.assert_array_equal(results[0], np.array([0.1, 0.2]))  # 从缓存
        np.testing.assert_array_equal(results[1], np.array([0.3, 0.4]))  # 新计算
        np.testing.assert_array_equal(results[2], np.array([0.5, 0.6]))  # 从缓存
        np.testing.assert_array_equal(results[3], np.array([0.7, 0.8]))  # 新计算
        
        print("✅ 批量嵌入缓存测试通过")


class TestOpenAIEmbeddingService:
    """OpenAIEmbeddingService单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.service = OpenAIEmbeddingService(use_cache=False)  # 禁用缓存以便测试
        self.service_with_cache = OpenAIEmbeddingService(use_cache=True)
    
    async def test_encode_empty_text(self):
        """测试编码空文本"""
        empty_results = [
            await self.service.encode_text(""),
            await self.service.encode_text("   "),
            await self.service.encode_text(None)
        ]
        
        for result in empty_results:
            assert isinstance(result, np.ndarray)
            assert result.shape == (self.service.dimension,)
            assert np.allclose(result, np.zeros(self.service.dimension))
        
        print("✅ 编码空文本测试通过")
    
    @patch('src.services.shared_openai_client.shared_client_manager')
    async def test_encode_text_success(self, mock_client_manager):
        """测试文本编码成功情况"""
        # Mock OpenAI response
        mock_response = AsyncMock()
        mock_response.data = [AsyncMock()]
        mock_response.data[0].embedding = [0.1] * self.service.dimension
        
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_client_manager.get_embedding_client.return_value = mock_client
        
        # 测试编码
        text = "Hello world"
        result = await self.service.encode_text(text)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (self.service.dimension,)
        assert not np.allclose(result, np.zeros(self.service.dimension))
        
        print("✅ 文本编码成功测试通过")
    
    @patch('src.services.shared_openai_client.shared_client_manager')
    async def test_encode_text_api_error(self, mock_client_manager):
        """测试API错误情况下的降级处理"""
        # Mock API error
        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_client_manager.get_embedding_client.return_value = mock_client
        
        # 测试编码
        text = "Test text for error handling"
        result = await self.service.encode_text(text)
        
        # 应该返回备用向量
        assert isinstance(result, np.ndarray)
        assert result.shape == (self.service.dimension,)
        # 备用向量应该是确定性的
        result2 = await self.service.encode_text(text)
        np.testing.assert_array_equal(result, result2)
        
        print("✅ API错误降级处理测试通过")
    
    @patch('src.services.shared_openai_client.shared_client_manager')
    async def test_encode_batch_success(self, mock_client_manager):
        """测试批量编码成功情况"""
        texts = ["text1", "text2", "text3"]
        
        # Mock OpenAI batch response
        mock_response = AsyncMock()
        mock_response.data = []
        for i in range(len(texts)):
            mock_data = AsyncMock()
            mock_data.embedding = [0.1 + i * 0.1] * self.service.dimension
            mock_response.data.append(mock_data)
        
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_client_manager.get_embedding_client.return_value = mock_client
        
        # 测试批量编码
        results = await self.service.encode_batch(texts)
        
        assert len(results) == len(texts)
        for i, result in enumerate(results):
            assert isinstance(result, np.ndarray)
            assert result.shape == (self.service.dimension,)
        
        print("✅ 批量编码成功测试通过")
    
    async def test_encode_batch_empty_list(self):
        """测试批量编码空列表"""
        results = await self.service.encode_batch([])
        assert results == []
        
        print("✅ 批量编码空列表测试通过")
    
    @patch('src.services.shared_openai_client.shared_client_manager')
    async def test_compute_similarity(self, mock_client_manager):
        """测试相似度计算"""
        # Mock identical embeddings for high similarity
        identical_embedding = [0.5] * self.service.dimension
        
        mock_response = AsyncMock()
        mock_response.data = [AsyncMock()]
        mock_response.data[0].embedding = identical_embedding
        
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_client_manager.get_embedding_client.return_value = mock_client
        
        # 测试相同文本的相似度
        similarity = await self.service.compute_similarity("same text", "same text")
        assert 0.9 <= similarity <= 1.0  # 应该很高
        
        print("✅ 相似度计算测试通过")
    
    @patch('src.services.shared_openai_client.shared_client_manager')
    async def test_find_similar_texts(self, mock_client_manager):
        """测试相似文本查找"""
        query = "search query"
        texts = ["similar text", "different content", "another match"]
        
        # Mock different embeddings for different similarities
        mock_responses = []
        embeddings = [
            [0.8] * self.service.dimension,  # query
            [0.7] * self.service.dimension,  # similar text
            [0.1] * self.service.dimension,  # different content  
            [0.6] * self.service.dimension,  # another match
        ]
        
        call_count = [0]
        async def mock_create(**kwargs):
            result = AsyncMock()
            result.data = [AsyncMock()]
            result.data[0].embedding = embeddings[call_count[0]]
            call_count[0] += 1
            return result
        
        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = mock_create
        mock_client_manager.get_embedding_client.return_value = mock_client
        
        # 测试查找相似文本
        results = await self.service.find_similar_texts(query, texts, top_k=2)
        
        assert len(results) <= 2
        assert all('text' in r and 'similarity' in r and 'index' in r for r in results)
        
        # 结果应该按相似度降序排列
        if len(results) > 1:
            assert results[0]['similarity'] >= results[1]['similarity']
        
        print("✅ 相似文本查找测试通过")
    
    @pytest.mark.asyncio 
    async def test_find_similar_texts_empty_inputs(self):
        """测试空输入的相似文本查找"""
        # 空查询
        results1 = await self.service.find_similar_texts("", ["text1", "text2"])
        assert results1 == []
        
        # 空文本列表
        results2 = await self.service.find_similar_texts("query", [])
        assert results2 == []
        
        print("✅ 空输入相似文本查找测试通过")
    
    def test_get_model_info(self):
        """测试模型信息获取"""
        info = self.service.get_model_info()
        
        required_fields = ['model_name', 'dimension', 'max_length', 'provider', 'api_based', 'cache_enabled']
        for field in required_fields:
            assert field in info
            
        assert info['provider'] == 'OpenAI'
        assert info['api_based'] is True
        assert info['cache_enabled'] is False  # 测试实例禁用了缓存
        
        print("✅ 模型信息获取测试通过")
    
    def test_cache_integration(self):
        """测试缓存集成"""
        service_info = self.service_with_cache.get_model_info()
        assert service_info['cache_enabled'] is True
        
        # 验证缓存对象存在
        assert self.service_with_cache.cache is not None
        assert hasattr(self.service_with_cache.cache, 'get_embedding')
        assert hasattr(self.service_with_cache.cache, 'get_batch_embeddings')
        
        print("✅ 缓存集成测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("🧪 开始OpenAI Embedding Service单元测试...")
    
    # EmbeddingCache tests
    cache_test = TestEmbeddingCache()
    cache_tests = [
        cache_test.test_cache_key_generation,
        cache_test.test_cache_put_and_get,
        cache_test.test_cache_persistence,
        cache_test.test_cache_size_limit,
        cache_test.test_get_embedding_with_cache,
        cache_test.test_get_batch_embeddings_with_cache
    ]
    
    # OpenAIEmbeddingService tests
    service_test = TestOpenAIEmbeddingService()
    service_tests = [
        service_test.test_encode_empty_text,
        service_test.test_encode_text_success,
        service_test.test_encode_text_api_error,
        service_test.test_encode_batch_success,
        service_test.test_encode_batch_empty_list,
        service_test.test_compute_similarity,
        service_test.test_find_similar_texts,
        service_test.test_find_similar_texts_empty_inputs,
        service_test.test_get_model_info,
        service_test.test_cache_integration
    ]
    
    all_tests = cache_tests + service_tests
    passed = 0
    failed = 0
    
    for test_func in all_tests:
        try:
            if hasattr(test_func, '__self__'):
                test_func.__self__.setup_method()
            
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
                
            if hasattr(test_func, '__self__'):
                test_func.__self__.teardown_method()
                
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 失败: {e}")
            failed += 1
            if hasattr(test_func, '__self__'):
                test_func.__self__.teardown_method()
    
    print(f"\n🎉 测试完成！通过: {passed}, 失败: {failed}")
    return failed == 0


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)
