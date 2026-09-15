from config import settings
from openai import AsyncOpenAI
import json


class OpenAIConfig:
    """Configuration settings for OpenAI API."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model_name = settings.MODEL_NAME
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate_response(self, prompt: str, pydantic_schema=None) -> dict:
        """Generate a structured response from the OpenAI chat API based on the given prompt."""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=5000,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response_schema",
                    "schema": pydantic_schema.model_json_schema(),
                    "strict": True,
                },
            },
        )
        return json.loads(response.choices[0].message.content)