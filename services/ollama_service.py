"""Service for interacting with Ollama vision models."""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel

from config import config

logger = logging.getLogger(__name__)


class EcoAnalysis(BaseModel):
    """Structured analysis result from the vision model."""

    product_name: str = "Unknown product"
    category: str = "unknown"
    recycling_guidance: str = "No guidance available."
    carbon_estimate_kg: float = 0.0
    greener_alternatives: str = "No alternatives found."
    raw_response: str = ""


ANALYSIS_PROMPT = """You are an eco-sustainability expert. Analyze this product or packaging image.

Respond ONLY with a JSON object. IMPORTANT: Every value must be a simple string or number. Do NOT use nested objects or arrays.

{
    "product_name": "the product or packaging name",
    "category": "one of: plastic, glass, paper, metal, organic, electronic, textile, mixed, unknown",
    "recycling_guidance": "Write plain English sentences here. Step 1: do this. Step 2: do that. Step 3: etc.",
    "carbon_estimate_kg": 0.5,
    "greener_alternatives": "Write plain English sentences here. Alternative 1: description. Alternative 2: description. Alternative 3: description."
}

Rules:
- recycling_guidance must be a single plain text string with sentences, NOT a nested object
- greener_alternatives must be a single plain text string with sentences, NOT an array
- carbon_estimate_kg must be a number (your best estimate in kg CO2e for this single item)
- Be specific, practical, and encouraging"""


class OllamaService:
    """Handles communication with Ollama API for image analysis."""

    def __init__(self) -> None:
        self.base_url = config.OLLAMA_BASE_URL
        self.model = config.OLLAMA_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)

    async def analyze_image(self, image_path: str) -> EcoAnalysis:
        """
        Send an image to Ollama vision model and get eco-analysis.

        Args:
            image_path: Path to the image file on disk.

        Returns:
            EcoAnalysis with structured recycling/carbon/alternatives data.
        """
        # Read and encode image
        image_bytes = Path(image_path).read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.model,
            "prompt": ANALYSIS_PROMPT,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            raw_text = result.get("response", "")
            logger.info("Ollama raw response: %s", raw_text[:200])

            return self._parse_response(raw_text)

        except httpx.HTTPStatusError as e:
            logger.error("Ollama HTTP error: %s", e)
            return EcoAnalysis(
                raw_response=str(e),
                recycling_guidance="Sorry, I couldn't analyze this image right now. Please try again.",
            )
        except httpx.RequestError as e:
            logger.error("Ollama connection error: %s", e)
            return EcoAnalysis(
                raw_response=str(e),
                recycling_guidance="Cannot connect to Ollama. Make sure it's running with a vision model loaded.",
            )

    def _parse_response(self, raw_text: str) -> EcoAnalysis:
        """Parse the JSON response from the model."""
        try:
            # Try to extract JSON from the response (model might wrap it in markdown)
            json_match = re.search(r"\{[\s\S]*\}", raw_text)
            if json_match:
                data = json.loads(json_match.group())
                return EcoAnalysis(
                    product_name=self._flatten(data.get("product_name", "Unknown product")),
                    category=self._flatten(data.get("category", "unknown")).lower(),
                    recycling_guidance=self._flatten(data.get("recycling_guidance", "No guidance available.")),
                    carbon_estimate_kg=self._extract_number(data.get("carbon_estimate_kg", 0.0)),
                    greener_alternatives=self._flatten(data.get("greener_alternatives", "No alternatives found.")),
                    raw_response=raw_text,
                )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse JSON from model response: %s", e)

        # Fallback: return raw text as guidance
        return EcoAnalysis(
            recycling_guidance=raw_text if raw_text else "Could not analyze the image.",
            raw_response=raw_text,
        )

    @staticmethod
    def _flatten(value) -> str:
        """Convert any value (dict, list, string) into a readable plain-text string."""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                if isinstance(v, str):
                    parts.append(f"{k}: {v}")
                elif isinstance(v, dict):
                    sub = ". ".join(f"{sk}: {sv}" for sk, sv in v.items() if isinstance(sv, str))
                    parts.append(f"{k}: {sub}")
                else:
                    parts.append(f"{k}: {v}")
            return ". ".join(parts)
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    sub = ". ".join(f"{v}" for v in item.values() if isinstance(v, str))
                    parts.append(sub)
                else:
                    parts.append(str(item))
            return ". ".join(parts)
        return str(value)

    @staticmethod
    def _extract_number(value) -> float:
        """Safely extract a float from various formats."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"[\d.]+", value)
            if match:
                return float(match.group())
        return 0.0

    async def check_health(self) -> bool:
        """Check if Ollama is reachable and the model is available."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            tags = response.json()
            models = [m["name"] for m in tags.get("models", [])]
            # Check if our model (or a variant) is available
            return any(self.model in m for m in models)
        except Exception as e:
            logger.error("Ollama health check failed: %s", e)
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
