"""
Base Pipeline Stage

Abstract base class for Red Team Pipeline stages.
Each stage takes input from the previous stage and produces output for the next.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage


@dataclass
class PipelineOutput:
    """Output from a pipeline stage"""
    stage_name: str
    data: Dict[str, Any]
    raw_response: str = ""
    success: bool = True
    error: Optional[str] = None


class PipelineStage(ABC):
    """
    Abstract base class for pipeline stages.
    
    Each stage:
    1. Receives input from previous stage (or scenario for first stage)
    2. Processes using LLM
    3. Returns structured output for next stage
    """

    def __init__(
        self,
        llm: BaseChatModel,
        cloud_provider: str = "aws",
        language: str = "terraform",
    ):
        """
        Initialize pipeline stage.
        
        Args:
            llm: LangChain chat model
            cloud_provider: Target cloud provider
            language: IaC language
        """
        self.llm = llm
        self.cloud_provider = cloud_provider
        self.language = language
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Return the name of this pipeline stage"""
        pass

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return the prompt template for this stage"""
        pass

    @abstractmethod
    def _format_prompt(self, input_data: Dict[str, Any]) -> str:
        """Format the prompt with input data"""
        pass

    @abstractmethod
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        pass

    async def execute(self, input_data: Dict[str, Any]) -> PipelineOutput:
        """
        Execute this pipeline stage.
        
        Args:
            input_data: Input from previous stage or scenario
            
        Returns:
            PipelineOutput with results for next stage
        """
        self.logger.info(f"Executing {self.stage_name}...")
        
        try:
            # Format prompt
            prompt = self._format_prompt(input_data)
            
            # Get LLM response
            response = await self._invoke_llm(prompt)
            
            # Parse response
            data = self._parse_response(response)
            
            self.logger.info(f"{self.stage_name} complete")
            
            return PipelineOutput(
                stage_name=self.stage_name,
                data=data,
                raw_response=response,
                success=True,
            )
            
        except Exception as e:
            self.logger.error(f"{self.stage_name} failed: {e}")
            return PipelineOutput(
                stage_name=self.stage_name,
                data={},
                success=False,
                error=str(e),
            )

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM with the given prompt."""
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            return content
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            raise

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text."""
        strategies = [
            lambda t: t.split("```json")[1].split("```")[0] if "```json" in t else None,
            lambda t: t.split("```")[1].split("```")[0] if t.count("```") >= 2 else None,
            lambda t: self._find_json_object(t),
            lambda t: t if t.strip().startswith("{") else None,
        ]
        
        for strategy in strategies:
            try:
                result = strategy(text)
                if result:
                    json.loads(result.strip())
                    return result.strip()
            except (json.JSONDecodeError, IndexError, TypeError):
                continue
        
        return None

    def _find_json_object(self, text: str) -> Optional[str]:
        """Find JSON object using brace matching."""
        start = text.find("{")
        if start == -1:
            return None
        
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        return None

    def _extract_between_markers(self, text: str, start_marker: str, end_marker: str) -> Optional[str]:
        """Extract text between markers."""
        try:
            start = text.index(start_marker) + len(start_marker)
            end = text.index(end_marker)
            return text[start:end].strip()
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Return stage configuration as dictionary."""
        return {
            "stage_type": self.__class__.__name__,
            "stage_name": self.stage_name,
            "cloud_provider": self.cloud_provider,
            "language": self.language,
        }
