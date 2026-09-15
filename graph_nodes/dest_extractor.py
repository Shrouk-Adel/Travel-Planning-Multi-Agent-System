from llm import OpenAIConfig
from prompts import *
from pydantic import BaseModel, Field
# =========================================================
# Destination extractor
# =========================================================
import logging

logger =logging.getLogger(__name__)


openai =OpenAIConfig()

class DestinationExtractorResponse(BaseModel):
    destination: str = Field(
        ...,
        description="The extracted destination from the user query."
    )

async def extract_destination(query: str) -> str:

    logger.info("extract destination")
    response = await openai.generate_response(
        prompt=destination_extractor_prompt.format(query=query),
        pydantic_schema=DestinationExtractorResponse
    )

    destination = response.destination.strip()  

    if not destination:
        raise ValueError(
            "The destination could not be extracted."
        )

    return destination