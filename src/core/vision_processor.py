import json
import re
import base64
from typing import Dict, Any, Optional
import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StructuredContent:
    """Structure for extracted content from vision APIs"""
    extracted_text: str
    layout_description: str
    ui_components: list
    content_type: str
    key_points: list
    full_summary: str
    confidence: float = 1.0
    
    def to_dict(self):
        return {
            'extracted_text': self.extracted_text,
            'layout_description': self.layout_description,
            'ui_components': self.ui_components,
            'content_type': self.content_type,
            'key_points': self.key_points,
            'full_summary': self.full_summary,
            'confidence': self.confidence,
            'timestamp': datetime.now().isoformat()
        }

class VisionProcessor:
    """Complete Vision Processor with full parsing logic"""
    
    def __init__(self, api_keys: Dict[str, str]):
        # Configure OpenRouter (Using OpenAI Client compat)
        openrouter_key = api_keys.get('openrouter') or api_keys.get('openai')
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
        )
        self.model = "qwen/qwen-2.5-vl-7b-instruct:free"  # Primary: Verified working & available
        
    def _extract_json_from_response(self, text: str) -> Optional[Dict]:
        """Extract JSON from API response (handles markdown code blocks)"""
        # Try to parse as plain JSON first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_patterns = [
            r'```json\s*(.*?)\s*```',  # ```json { ... } ```
            r'```\s*(.*?)\s*```',      # ``` { ... } ```
            r'{(.*)}',                  # Just extract between braces
        ]
        
        for pattern in json_patterns:
            matches = re.search(pattern, text, re.DOTALL)
            if matches:
                try:
                    # Treat the captured group as the full JSON string
                    content = matches.group(1).strip()
                    # If it doesn't start with brace and look like JSON, finding { first might be safer, 
                    # but usually markdown blocks contain the full object.
                    return json.loads(content)
                except (json.JSONDecodeError, AttributeError):
                    continue
        
        return None
    

    

    

    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def process_with_openrouter(self, image_path: str) -> Dict[str, Any]:
        """Process using OpenRouter Free Vision Models"""
        
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
        prompt = """Extract all content from this screenshot with perfect accuracy.
        Return ONLY a JSON object with these exact fields:
        - extracted_text: All text exactly as seen
        - layout_description: Spatial arrangement of elements
        - ui_components: List of UI elements identified
        - content_type: Type of content (document/dashboard/app/website/code)
        - key_points: List of important information
        - full_summary: Concise summary preserving all context
        
        No other text, only JSON."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                extra_headers={
                    "HTTP-Referer": "https://taskmaster-ai.com",
                    "X-Title": "TaskMaster AI"
                }
            )
            
            content = response.choices[0].message.content
            data = self._extract_json_from_response(content)
            
            if not data:
                # Basic Fallback
                return {
                    "extracted_text": content[:500],
                    "full_summary": "Extracted via OpenRouter fallback",
                    "confidence": 0.5
                }
                
            return {
                "extracted_text": data.get("extracted_text", ""),
                "layout_description": data.get("layout_description", ""),
                "ui_components": data.get("ui_components", []),
                "content_type": data.get("content_type", "unknown"),
                "key_points": data.get("key_points", []),
                "full_summary": data.get("full_summary", ""),
                "confidence": 0.95
            }
            
        except Exception as e:
            print(f"OpenRouter API Error: {e}")
            raise
    
    async def process_hybrid(self, image_path: str) -> Dict[str, Any]:
        """Main processing method (OpenRouter Processing)"""
        try:
            # Try Qwen 2.5 VL first
            return await self.process_with_openrouter(image_path)
        except Exception as e:
            # Fallback to Gemini if Qwen fails
            print(f"Primary model failed, trying fallback: {e}")
            self.model = "google/gemini-2.0-flash-exp:free"
            return await self.process_with_openrouter(image_path)