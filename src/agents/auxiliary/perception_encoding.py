"""
Perception Encoding Agent
感知编码智能体

负责感知输入的编码和预处理
- 多模态感知融合 (视觉、听觉、语义)
- 注意力机制和显著性检测
- 特征提取和编码
- 对应大脑区域: 初级感觉皮层、颞叶、枕叶
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from ..base import BrainAgent, AgentMessage

logger = logging.getLogger(__name__)

@dataclass
class PerceptualInput:
    """感知输入数据结构"""
    input_type: str  # "text", "visual", "audio", "multimodal"
    content: str
    raw_data: Optional[Any] = None
    attention_weight: float = 1.0
    salience_score: float = 0.5
    encoding_features: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.encoding_features is None:
            self.encoding_features = {}

class PerceptionEncodingAgent(BrainAgent):
    """
    感知编码智能体
    
    模拟大脑的感知编码过程:
    - 初级感觉皮层的特征检测
    - 注意力机制和选择性处理
    - 多模态信息融合
    - 编码质量评估
    """
    
    def __init__(self, agent_id: str = "perception_encoding"):
        system_prompt = """
        你是感知编码智能体，负责处理和编码各种感知输入。
        
        核心职责:
        1. 多模态感知融合 - 整合不同类型的感知输入
        2. 注意力机制 - 识别和突出重要信息
        3. 特征提取 - 提取关键特征用于后续处理
        4. 编码质量控制 - 确保编码的准确性和完整性
        
        处理原则:
        - 优先处理高显著性信息
        - 保持多模态信息的一致性
        - 适应不同类型输入的编码策略
        - 维持注意力资源的有效分配
        
        输出格式应包含编码特征、注意力权重、显著性评分等信息。
        """
        super().__init__(agent_id, "sensory_cortex", system_prompt)
        self.attention_capacity = 7  # 注意力容量限制
        self.current_focus = []
        self.encoding_strategies = {
            "text": self._encode_text,
            "visual": self._encode_visual,
            "audio": self._encode_audio,
            "multimodal": self._encode_multimodal
        }
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """处理感知编码请求"""
        try:
            if message.message_type == "encode_perception":
                result = await self._encode_perception(message.content)
                return AgentMessage(
                    sender=self.agent_id,
                    receiver=message.sender,
                    message_type="perception_encoded",
                    content=result
                )
            else:
                return await super().process_message(message)
        except Exception as e:
            logger.error(f"Perception encoding error: {e}")
            return AgentMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type="error",
                content={"error": f"感知编码失败: {str(e)}"}
            )
    
    async def _encode_perception(self, perception_data: Dict) -> Dict[str, Any]:
        """编码感知输入"""
        input_type = perception_data.get("type", "text")
        content = perception_data.get("content", "")
        
        # 创建感知输入对象
        perceptual_input = PerceptualInput(
            input_type=input_type,
            content=content,
            raw_data=perception_data.get("raw_data")
        )
        
        # 计算显著性和注意力权重
        perceptual_input.salience_score = await self._calculate_salience(perceptual_input)
        perceptual_input.attention_weight = await self._allocate_attention(perceptual_input)
        
        # 执行编码
        encoding_strategy = self.encoding_strategies.get(input_type, self._encode_text)
        encoded_features = await encoding_strategy(perceptual_input)
        
        # 更新注意力焦点
        self._update_attention_focus(perceptual_input)
        
        return {
            "encoded_features": encoded_features,
            "attention_weight": perceptual_input.attention_weight,
            "salience_score": perceptual_input.salience_score,
            "input_type": input_type,
            "processing_quality": await self._assess_encoding_quality(encoded_features),
            "attention_state": self.current_focus[-3:] if self.current_focus else []
        }
    
    async def _calculate_salience(self, perceptual_input: PerceptualInput) -> float:
        """计算感知输入的显著性"""
        # 使用LLM分析显著性
        prompt = f"""
        分析以下感知输入的显著性程度，考虑:
        1. 新颖性和意外性
        2. 情绪相关性
        3. 任务相关性
        4. 感知强度
        
        输入类型: {perceptual_input.input_type}
        内容: {perceptual_input.content[:200]}
        
        请返回0-1之间的显著性评分，其中1表示极高显著性。
        只返回数字，不要其他解释。
        """
        
        try:
            response = await self.call_llm(prompt, max_tokens=10)
            salience = float(response.strip())
            return max(0.0, min(1.0, salience))
        except:
            return 0.5  # 默认中等显著性
    
    async def _allocate_attention(self, perceptual_input: PerceptualInput) -> float:
        """分配注意力权重"""
        base_weight = perceptual_input.salience_score
        
        # 考虑当前注意力负载
        current_load = len(self.current_focus) / self.attention_capacity
        attention_factor = 1.0 - (current_load * 0.5)
        
        # 考虑输入类型优先级
        type_priority = {
            "multimodal": 1.0,
            "visual": 0.9,
            "text": 0.8,
            "audio": 0.7
        }
        
        priority_factor = type_priority.get(perceptual_input.input_type, 0.8)
        
        return base_weight * attention_factor * priority_factor
    
    async def _encode_text(self, perceptual_input: PerceptualInput) -> Dict[str, Any]:
        """编码文本输入"""
        content = perceptual_input.content
        
        # 语义特征提取
        semantic_prompt = f"""
        提取以下文本的关键语义特征:
        文本: {content}
        
        请提取:
        1. 主题关键词 (最多5个)
        2. 情绪倾向 (positive/negative/neutral)
        3. 抽象级别 (concrete/abstract)
        4. 时间信息 (past/present/future/none)
        5. 实体信息 (人物、地点、事物)
        
        以JSON格式返回。
        """
        
        try:
            semantic_features = await self.call_llm(semantic_prompt, max_tokens=200)
            # 简化处理，实际应解析JSON
            features = {
                "semantic_content": content,
                "encoding_type": "linguistic",
                "feature_vector": content[:100],  # 简化的特征向量
                "complexity": min(1.0, len(content) / 500),
                "semantic_density": len(content.split()) / max(1, len(content.split('.')))
            }
        except Exception as e:
            features = {
                "semantic_content": content,
                "encoding_type": "linguistic",
                "error": str(e)
            }
        
        return features
    
    async def _encode_visual(self, perceptual_input: PerceptualInput) -> Dict[str, Any]:
        """编码视觉输入"""
        # 模拟视觉特征编码
        return {
            "visual_features": "模拟视觉特征",
            "encoding_type": "visual",
            "spatial_info": "空间布局信息",
            "color_info": "颜色信息",
            "shape_info": "形状信息",
            "motion_info": "运动信息"
        }
    
    async def _encode_audio(self, perceptual_input: PerceptualInput) -> Dict[str, Any]:
        """编码听觉输入"""
        # 模拟听觉特征编码
        return {
            "audio_features": "模拟听觉特征",
            "encoding_type": "auditory",
            "frequency_info": "频率信息",
            "rhythm_info": "节律信息",
            "phonetic_info": "语音信息"
        }
    
    async def _encode_multimodal(self, perceptual_input: PerceptualInput) -> Dict[str, Any]:
        """编码多模态输入"""
        # 模拟多模态融合编码
        return {
            "multimodal_features": "融合特征",
            "encoding_type": "multimodal",
            "cross_modal_binding": "跨模态绑定信息",
            "integration_confidence": 0.8
        }
    
    def _update_attention_focus(self, perceptual_input: PerceptualInput):
        """更新注意力焦点"""
        focus_item = {
            "content": perceptual_input.content[:50],
            "type": perceptual_input.input_type,
            "attention_weight": perceptual_input.attention_weight,
            "timestamp": "current"
        }
        
        self.current_focus.append(focus_item)
        
        # 维持注意力容量限制
        if len(self.current_focus) > self.attention_capacity:
            # 移除注意力权重最低的项目
            self.current_focus.sort(key=lambda x: x["attention_weight"], reverse=True)
            self.current_focus = self.current_focus[:self.attention_capacity]
    
    async def _assess_encoding_quality(self, encoded_features: Dict[str, Any]) -> float:
        """评估编码质量"""
        quality_factors = []
        
        # 特征完整性
        if "encoding_type" in encoded_features:
            quality_factors.append(0.8)
        
        # 特征丰富度
        feature_count = len([k for k in encoded_features.keys() if not k.startswith("_")])
        richness = min(1.0, feature_count / 5.0)
        quality_factors.append(richness)
        
        # 处理成功率
        if "error" not in encoded_features:
            quality_factors.append(0.9)
        else:
            quality_factors.append(0.3)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
    
    async def get_attention_state(self) -> Dict[str, Any]:
        """获取当前注意力状态"""
        return {
            "current_focus": self.current_focus,
            "attention_capacity": self.attention_capacity,
            "load_factor": len(self.current_focus) / self.attention_capacity,
            "dominant_modality": self._get_dominant_modality()
        }
    
    def _get_dominant_modality(self) -> str:
        """获取主导模态"""
        if not self.current_focus:
            return "none"
        
        modality_counts = {}
        for item in self.current_focus:
            modality = item["type"]
            modality_counts[modality] = modality_counts.get(modality, 0) + 1
        
        return max(modality_counts.items(), key=lambda x: x[1])[0] if modality_counts else "none"