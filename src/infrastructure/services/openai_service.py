from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)

# Load prompt from file
PROMPTS_DIR = Path(__file__).parent / "prompts"
MILK_PRODUCTION_PROMPT = (PROMPTS_DIR / "milk_production_ocr.txt").read_text(encoding="utf-8")


class MilkRecord(TypedDict):
    name: str
    liters: float


class OpenAIService:
    """Service for OpenAI Vision API integration."""

    def __init__(self, api_key: str):
        """Initialize OpenAI service with API key."""
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)

    async def extract_milk_records(self, image_url: str) -> list[MilkRecord]:
        """
        Extract milk production records from an image using GPT-4o-mini Vision.

        Args:
            image_url: Public URL of the image to process

        Returns:
            List of milk records with name and liters

        Raises:
            ValueError: If OpenAI response is invalid or cannot be parsed
            Exception: For OpenAI API errors
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": MILK_PRODUCTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "high",  # Better precision for text
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,  # Enough for ~30-40 records
                temperature=0.1,  # Low for consistency
            )

            # Extract and parse response
            try:
                content = response.choices[0].message.content
            except Exception as resp_e:
                logger.error("Failed to read response content: %s", resp_e)
                raise
            if not content:
                raise ValueError("Empty response from OpenAI")

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON if wrapped in markdown code blocks
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    data = json.loads(content)
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    data = json.loads(content)
                else:
                    raise

            # Validate structure
            if "records" not in data:
                raise ValueError("Response missing 'records' field")

            records: list[MilkRecord] = []
            for idx, item in enumerate(data["records"]):
                if "name" not in item or "liters" not in item:
                    logger.debug("Skipping invalid record at index %s", idx)
                    continue

                name_val = item.get("name")
                liters_val = item.get("liters")

                # Skip null liters values
                if liters_val is None:
                    logger.debug("Skipping record idx=%s due to null liters", idx)
                    continue

                try:
                    liters_float = float(liters_val)
                except Exception:
                    logger.debug("Skipping record idx=%s: cannot convert liters", idx)
                    continue

                records.append({"name": str(name_val), "liters": liters_float})

            return records

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {content[:200]}") from e

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
