import json
import time
from typing import List, Dict, Optional, Any
from openai import OpenAI
from . import config

class LLMClient:
    def __init__(self, 
                 model_name: str = config.MODEL_NAME, 
                 base_url: str = config.MODEL_BASE_URL, 
                 api_key: str = config.MODEL_API_KEY, 
                 temperature: float = config.TEMPERATURE):
        self.model_name = model_name
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.temperature = temperature
        self.max_retries = config.MAX_RETRIES
        self.trace: List[Dict[str, Any]] = []

    def _execute_with_retry(self, **kwargs) -> Any:
        retries = 0
        while retries < self.max_retries:
            try:
                response = self.client.chat.completions.create(**kwargs)
                self.trace.append({
                    "timestamp": time.time(),
                    "request": kwargs,
                    "response": response.model_dump(),
                    "status": "success"
                })
                return response
            except Exception as e:
                retries += 1
                self.trace.append({
                    "timestamp": time.time(),
                    "request": kwargs,
                    "error": str(e),
                    "status": "error",
                    "retry_count": retries
                })
                if retries >= self.max_retries:
                    raise
                time.sleep(2 ** retries) # Exponential backoff

    def chat(self, messages: List[Dict[str, str]], response_format: Optional[Dict[str, str]] = None) -> str:
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self._execute_with_retry(**kwargs)
        return response.choices[0].message.content

    def chat_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        content = self.chat(messages, response_format={"type": "json_object"})
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Simple fallback if JSON parsing fails, though API should return valid JSON
            raise ValueError(f"Failed to parse JSON response: {content}") from e

    def get_trace(self) -> List[Dict[str, Any]]:
        return self.trace
