from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import json
import logging

class BaseAgent(ABC):
    """Base class for all dispute resolution agents."""
    
    def __init__(self, name: str, llm_client, data_access):
        self.name = name
        self.llm = llm_client
        self.data = data_access  # DataAccess instance for CSV queries
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the case and return results.
        
        Args:
            context: Shared context dict with case info and results from other agents
        Returns:
            Dict with this agent's analysis results
        """
        pass
    
    def _build_prompt(self, system: str, user: str) -> list:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    
    def _safe_json_parse(self, text: str) -> Optional[Dict]:
        """Safely parse JSON from LLM response."""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            self.logger.warning(f"[{self.name}] Failed to parse JSON from LLM response")
            return None
