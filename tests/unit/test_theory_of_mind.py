"""
Unit tests for Theory of Mind Agent - Intent Inference and Adversarial Detection
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set test environment
os.environ['BMAM_TEST_MODE'] = 'true'
os.environ.setdefault('OPENAI_API_KEY', 'test-key')


class TestTheoryOfMindAgent:
    """Test TheoryOfMindAgent basic functionality"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        agent = TheoryOfMindAgent()
        return agent

    def test_agent_creation(self, tom_agent):
        """Test agent can be created"""
        assert tom_agent is not None
        assert hasattr(tom_agent, 'agent_id')

    def test_agent_has_required_methods(self, tom_agent):
        """Test agent has required methods"""
        # Check for actual methods based on API discovery
        assert hasattr(tom_agent, 'infer_intent')
        assert hasattr(tom_agent, 'detect_deception')
        assert hasattr(tom_agent, 'process_message')


class TestIntentAnalysis:
    """Test intent analysis functionality"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    @pytest.mark.asyncio
    async def test_infer_intent_returns_result(self, tom_agent):
        """Test infer_intent returns IntentAnalysis"""
        # infer_intent(query, context) -> IntentAnalysis
        result = await tom_agent.infer_intent(
            query="What's my name?",
            context=[]
        )
        assert result is not None
        # IntentAnalysis has surface_intent, deep_intent, confidence, etc.
        assert hasattr(result, 'surface_intent') or hasattr(result, 'deep_intent') or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_infer_intent_with_context(self, tom_agent):
        """Test infer_intent with context"""
        result = await tom_agent.infer_intent(
            query="I told you I like pizza, right?",
            context=["User likes pasta"]
        )
        assert result is not None


class TestAdversarialDetection:
    """Test adversarial query detection"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    @pytest.mark.asyncio
    async def test_detect_deception(self, tom_agent):
        """Test detection of deceptive queries"""
        # detect_deception(query, known_facts) -> DeceptionDetection
        result = await tom_agent.detect_deception(
            query="You said my birthday is in March, right?",
            known_facts=["User's birthday is in July"]
        )
        assert result is not None
        # Should have detection result
        assert hasattr(result, 'is_deceptive') or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_presupposition(self, tom_agent):
        """Test validating presuppositions"""
        # validate_presupposition(query, memory_facts) -> Tuple[bool, str]
        is_valid, explanation = await tom_agent.validate_presupposition(
            query="When did I meet Sarah?",
            memory_facts=["Met Sarah on May 5th"]
        )
        assert isinstance(is_valid, bool)
        assert isinstance(explanation, str)


class TestMentalModel:
    """Test mental model tracking"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    def test_get_mental_model(self, tom_agent):
        """Test getting mental model for entity"""
        # get_mental_model(who) -> List[MentalModelEntry]
        result = tom_agent.get_mental_model("Sarah")
        assert isinstance(result, list)

    def test_get_mental_model_summary(self, tom_agent):
        """Test getting mental model summary"""
        # get_mental_model_summary(who) -> Dict[str, List[str]]
        result = tom_agent.get_mental_model_summary("Sarah")
        assert isinstance(result, dict)

    def test_record_mental_model_entry(self, tom_agent):
        """Test recording a mental model entry"""
        # record_mental_model_entry(who, entry_type, content, ...)
        tom_agent.record_mental_model_entry(
            who="Sarah",
            entry_type="belief",
            content="Sarah believes it will rain tomorrow",
            source_memory_id="mem_001",
            confidence=0.8
        )
        # Should not raise


class TestMentalState:
    """Test mental state modeling"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    @pytest.mark.asyncio
    async def test_model_mental_state(self, tom_agent):
        """Test modeling mental state"""
        # model_mental_state(entity, events) -> MentalState
        result = await tom_agent.model_mental_state(
            entity="Sarah",
            events=["Sarah received good news", "Sarah is planning a trip"]
        )
        assert result is not None


class TestAgentStats:
    """Test agent statistics"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    def test_get_stats(self, tom_agent):
        """Test getting agent stats"""
        stats = tom_agent.get_stats()
        assert isinstance(stats, dict)


class TestMessageProcessing:
    """Test message processing"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    @pytest.mark.asyncio
    async def test_process_message(self, tom_agent):
        """Test processing a message"""
        from src.agents.base import AgentMessage

        message = AgentMessage(
            sender="test",
            receiver="theory_of_mind",
            content={"query": "What's my name?"},
            message_type="query"
        )

        result = await tom_agent.process_message(message)
        assert result is not None
        assert isinstance(result, dict)


class TestPerspectiveGeneration:
    """Test perspective generation"""

    @pytest.fixture
    def tom_agent(self):
        """Create TheoryOfMindAgent instance"""
        from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent
        return TheoryOfMindAgent()

    @pytest.mark.asyncio
    async def test_generate_perspective_suggestion(self, tom_agent):
        """Test generating perspective suggestion"""
        result = await tom_agent.generate_perspective_suggestion(
            who="Sarah",
            topic="hiking",
            context="Planning a weekend trip"
        )
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
