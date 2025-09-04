import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
import logging
import time

class APIClient:
    """Client for making API calls to DeepSeek and other services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('deepseek_api_key', '')
        self.base_url = config.get('base_url', 'https://api.deepseek.com')
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.logger = logging.getLogger('ma-cmm.api_client')
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
        # Cost tracking
        self.total_cost = 0.0
        self.request_count = 0
        self.cost_per_request = {
            'deepseek-reasoner': 0.01,  # Estimated cost per request
            'deepseek-chat': 0.005
        }
    
    async def generate(self, prompt: str, model: str = "deepseek-chat", 
                      temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate text using the specified model"""
        
        if not self.api_key:
            raise ValueError("API key not configured")
        
        # Rate limiting
        await self._rate_limit()
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        url = f"{self.base_url}/v1/chat/completions"
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result['choices'][0]['message']['content']
                            
                            # Update cost tracking
                            self.request_count += 1
                            self.total_cost += self.cost_per_request.get(model, 0.005)
                            
                            self.logger.info(f"API call successful. Model: {model}, Cost: ${self.total_cost:.4f}")
                            return content
                        
                        elif response.status == 429:  # Rate limit
                            wait_time = 2 ** attempt
                            self.logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        else:
                            error_text = await response.text()
                            self.logger.error(f"API error {response.status}: {error_text}")
                            if attempt == self.max_retries - 1:
                                raise Exception(f"API request failed with status {response.status}")
                            await asyncio.sleep(2 ** attempt)
            
            except asyncio.TimeoutError:
                self.logger.warning(f"API timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise Exception("API request timed out after all retries")
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                self.logger.error(f"API request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("API request failed after all retries")
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def get_cost_info(self) -> Dict[str, Any]:
        """Get current cost information"""
        return {
            'total_cost': self.total_cost,
            'request_count': self.request_count,
            'average_cost_per_request': self.total_cost / max(1, self.request_count)
        }
    
    def reset_cost_tracking(self):
        """Reset cost tracking counters"""
        self.total_cost = 0.0
        self.request_count = 0


class MockAPIClient:
    """Mock API client for testing without actual API calls"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger('ma-cmm.mock_api_client')
        self.request_count = 0
        self.total_cost = 0.0
    
    async def generate(self, prompt: str, model: str = "deepseek-chat", 
                      temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Mock text generation"""
        self.request_count += 1
        self.total_cost += 0.001  # Mock cost
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Return different responses based on model and prompt content
        if 'condition' in prompt.lower():
            return self._mock_condition_extraction()
        elif 'conflict' in prompt.lower():
            return self._mock_conflict_analysis()
        elif 'compress' in prompt.lower():
            return self._mock_compression_advice()
        else:
            return self._mock_general_response(prompt)
    
    def _mock_condition_extraction(self) -> str:
        """Mock condition extraction response"""
        return json.dumps({
            "hard_constraints": [
                {
                    "text": "Must be completed by Friday",
                    "source_turn": 2,
                    "confidence": "high"
                }
            ],
            "soft_preferences": [
                {
                    "text": "Prefer morning appointments",
                    "source_turn": 1,
                    "confidence": "medium"
                }
            ],
            "temporal_conditions": [
                {
                    "text": "By end of week",
                    "source_turn": 2,
                    "confidence": "high"
                }
            ],
            "negations": []
        })
    
    def _mock_conflict_analysis(self) -> str:
        """Mock conflict analysis response"""
        return """
Conflict Analysis Result:
Type: temporal_conflict
Explanation: The user specified both "today" and "tomorrow" for the same task, which creates a temporal inconsistency.
Severity: medium
Recommendation: Keep the more recent temporal specification and clarify with user if needed.
"""
    
    def _mock_compression_advice(self) -> str:
        """Mock compression advice"""
        return """
Compression Recommendations:
1. Remove conditions with importance score < 0.3 and access count = 0
2. Merge similar soft preferences about the same topic
3. Keep all hard constraints (never remove)
4. Consider removing temporal conditions that are no longer relevant
"""
    
    def _mock_general_response(self, prompt: str) -> str:
        """Mock general response"""
        return f"This is a mock response to the query. The prompt contained {len(prompt.split())} words. In a real implementation, this would be generated by the DeepSeek API based on the provided context and conditions."
    
    def get_cost_info(self) -> Dict[str, Any]:
        """Get mock cost information"""
        return {
            'total_cost': self.total_cost,
            'request_count': self.request_count,
            'average_cost_per_request': self.total_cost / max(1, self.request_count)
        }
    
    def reset_cost_tracking(self):
        """Reset cost tracking counters"""
        self.total_cost = 0.0
        self.request_count = 0