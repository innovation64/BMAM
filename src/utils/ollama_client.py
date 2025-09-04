import aiohttp
import json
from typing import Dict, Any
import logging
import asyncio

class OllamaClient:
    """Client for local Ollama models"""
    
    # Class-level caches (shared across all instances)
    _global_connectivity_checked = False
    _global_available_models = None
    _global_base_url = None
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.timeout = config.get('timeout', 60)
        self.logger = logging.getLogger('ma-cmm.ollama_client')
        self.request_count = 0
        self.total_cost = 0.0  # No cost for local models
        
        # Reset global cache if base_url changed
        if OllamaClient._global_base_url != self.base_url:
            OllamaClient._global_connectivity_checked = False
            OllamaClient._global_available_models = None
            OllamaClient._global_base_url = self.base_url
    
    async def check_connectivity(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Only log once globally (disabled for cleaner output)
                        if not OllamaClient._global_connectivity_checked:
                            # self.logger.info("Ollama is running and accessible")  # Disabled
                            OllamaClient._global_connectivity_checked = True
                        return True
        except Exception as e:
            self.logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
        return False
    
    async def list_models(self) -> list:
        """List available models with global caching"""
        # Return cached models if available
        if OllamaClient._global_available_models is not None:
            return OllamaClient._global_available_models
            
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        models = [model['name'] for model in result.get('models', [])]
                        # Cache the models globally (disabled logging for cleaner output)
                        if OllamaClient._global_available_models is None:
                            # self.logger.info(f"Available models: {models}")  # Disabled
                            pass
                        OllamaClient._global_available_models = models
                        return models
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
        return []
    
    async def generate(self, prompt: str, model: str = "llama3.1:8b", 
                      temperature: float = 0.7, max_tokens: int = 1000, 
                      enforce_json: bool = False) -> str:
        """Generate text using Ollama"""
        
        # Check connectivity first
        if not await self.check_connectivity():
            error_msg = (
                f"Cannot connect to Ollama at {self.base_url}. "
                "Please ensure Ollama is running with: ollama serve"
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Check if model exists (only if we haven't cached models yet)
        if OllamaClient._global_available_models is None:
            models = await self.list_models()
            if models and model not in models:
                self.logger.warning(f"Model {model} not found. Available models: {models}")
                if not models:
                    error_msg = (
                        f"No models found. Please pull the model first with: "
                        f"ollama pull {model}"
                    )
                    self.logger.error(error_msg)
                    raise Exception(error_msg)
        elif model not in OllamaClient._global_available_models:
            # Use cached models for check
            self.logger.warning(f"Model {model} not found in cached models: {OllamaClient._global_available_models}")
        
        # Add JSON formatting instruction if requested
        if enforce_json and not any(keyword in prompt.lower() for keyword in ['json', 'format', 'structure']):
            prompt = f"{prompt}\n\nPlease provide your response in valid JSON format."
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        url = f"{self.base_url}/api/generate"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            self.request_count += 1
                            response_text = result.get('response', '')
                            
                            # Log warning if response looks like it might contain JSON parsing issues
                            if not response_text.strip():
                                self.logger.warning("Empty response from Ollama")
                            elif response_text.startswith("Based on") and "JSON" in response_text:
                                self.logger.warning("Model response mentions JSON parsing - possible format issue")
                            
                            return response_text
                        except json.JSONDecodeError as e:
                            # If JSON parsing fails, get raw text
                            raw_text = await response.text()
                            self.logger.error(f"JSON parsing failed: {e}")
                            self.logger.error(f"Raw response: {raw_text[:500]}...")
                            
                            # Try to extract meaningful content from raw response
                            if raw_text.strip():
                                self.logger.warning("Using raw text response due to JSON parsing failure")
                                return raw_text
                            else:
                                raise Exception(f"JSON parsing failed and no content: {e}")
                    elif response.status == 404:
                        error_text = await response.text()
                        error_msg = (
                            f"Ollama API endpoint not found (404). "
                            f"This might mean:\n"
                            f"1. Ollama is not running - start it with: ollama serve\n"
                            f"2. The model '{model}' is not pulled - run: ollama pull {model}\n"
                            f"3. The API endpoint has changed\n"
                            f"Error details: {error_text}"
                        )
                        raise Exception(error_msg)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama error {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            error_msg = (
                f"Network error connecting to Ollama: {e}\n"
                f"Please check:\n"
                f"1. Is Ollama running? Start with: ollama serve\n"
                f"2. Is it listening on {self.base_url}?\n"
                f"3. Check firewall/network settings"
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            self.logger.error(f"Ollama request failed: {e}")
            raise
    
    def get_cost_info(self) -> Dict[str, Any]:
        """Get cost info (free for local models)"""
        return {
            'total_cost': 0.0,
            'request_count': self.request_count,
            'average_cost_per_request': 0.0
        }
    
    def reset_cost_tracking(self):
        """Reset tracking"""
        self.request_count = 0
    
    async def generate_response(self, prompt: str, model: str = "llama3.1:8b", 
                               temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate response using Ollama (alias for generate method)"""
        return await self.generate(prompt, model, temperature, max_tokens)