from config import settings
from openai import OpenAI
import json


class OpenAIConfig:
    """Configuration settings for OpenAI API."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model_name = settings.model_name

    async def generate_response(self,prompt,pydantic_schema) -> str:
        """Generate a response from the OpenAI API based on the given prompt."""
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.Completions.create(
            model=self.model_name,
            max_tokens=2000,
            prompt=prompt,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response_schema",
                    "schema": pydantic_schema.model_json_schema(),
                    "strict": True
                }
            }

        )
        return json.loads(response.choices[0].text.strip())