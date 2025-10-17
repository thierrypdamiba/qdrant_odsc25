"""Groq LLM service implementation"""
from typing import AsyncIterator


class GroqLLMService:
    """Groq LLM service implementation"""
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
    
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a response using Groq"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        return response.choices[0].message.content
    
    async def generate_stream(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        """Generate a streaming response using Groq"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


