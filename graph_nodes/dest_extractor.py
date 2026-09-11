from llm import OpenAIConfig
from ..prompts import *
from pydantic import BaseModel, Field
# =========================================================
# Destination extractor
# =========================================================


openai =OpenAIConfig()

class DestinationExtractorResponse(BaseModel):
    destination: str = Field(
        ...,
        description="The extracted destination from the user query."
    )

def extract_destination(query: str) -> str:


    response = openai.generate_response(
        user_prompt=destination_extractor_prompt.format(query=query),
        system_prompt=destination_extractor_prompt,
        pydantic_schema=DestinationExtractorResponse
    )

    destination = response.destination.strip()  

    if not destination:
        raise ValueError(
            "The destination could not be extracted."
        )

    return destination