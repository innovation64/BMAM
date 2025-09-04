#!/usr/bin/env python3
"""
OpenAI API Client for MA-CMM system
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional
import logging
from openai import AsyncOpenAI


class OpenAIClient:
    """Client for making API calls to OpenAI"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get API key from environment or config
        self.api_key = (
            os.getenv('OPENAI_API_KEY') or 
            self.config.get('openai_api_key', '')
        )
        
        self.base_url = self.config.get('base_url', 'https://api.openai.com/v1')
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.logger = logging.getLogger('ma-cmm.openai_client')
        
        # Initialize OpenAI client
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            self.logger.info("OpenAI client initialized successfully")
        else:
            self.client = None
            self.logger.warning("No OpenAI API key found, client not initialized")
        
        # Cost tracking
        self.total_cost = 0.0
        self.request_count = 0
    
    async def generate(self, prompt: str, model: str = "gpt-4o-mini", 
                      max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate response using OpenAI API"""
        if not self.client:
            raise Exception("OpenAI client not initialized - missing API key")
        
        try:
            self.logger.info(f"Making OpenAI API call with model: {model}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            self.request_count += 1
            result = response.choices[0].message.content
            
            self.logger.info(f"OpenAI API call successful, response length: {len(result)}")
            return result
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            raise e
    
    async def generate_response(self, prompt: str, max_tokens: int = 500, 
                               temperature: float = 0.7, model: str = "gpt-4o-mini") -> str:
        """Alias for generate method for compatibility"""
        return await self.generate(prompt, model, max_tokens, temperature)
    
    def get_cost_info(self) -> Dict[str, Any]:
        """Get cost tracking information"""
        return {
            "total_requests": self.request_count,
            "estimated_cost": self.total_cost,
            "api_key_configured": bool(self.api_key)
        }
    
    def reset_cost_tracking(self):
        """Reset cost tracking counters"""
        self.total_cost = 0.0
        self.request_count = 0