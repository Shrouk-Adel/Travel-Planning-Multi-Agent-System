import json
import logging
import re
from config import settings
from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


_IATA_FALLBACK_PATTERN = re.compile(r'\b([A-Z]{3})\b')

_FENCE_PATTERN = re.compile(r'^```(?:json)?\s*|\s*```$', re.MULTILINE)

class OpenAIConfig:
    def __init__(self):
            self.api_key = settings.OPENAI_API_KEY
            self.base_url = settings.OPENAI_BASE_URL
            self.model_name = settings.MODEL_NAME
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
 

    async def generate_response(
        self,
        prompt: str,
        pydantic_schema: type[BaseModel] | None = None,
        **kwargs,
    ) -> dict | None:
        """Call the chat completion endpoint and parse the result as JSON.

        Defensive against the failure modes we actually hit:
          - empty `content` (some local servers return "" instead of erroring)
          - content wrapped in ```json ... ``` fences
          - content that's valid prose but not JSON at all (model ignored
            the schema instruction) — logged clearly, returns None rather
            than raising, so callers can fall back gracefully instead of
            crashing per-item.

        Returns a plain dict (schema-validated if `pydantic_schema` is
        given and validation succeeds), or None on any failure.
        """
        request_kwargs = dict(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        if pydantic_schema is not None:
            # Ask for strict JSON-schema-constrained output where the
            # server supports it (OpenAI proper, and some local servers
            # like recent llama.cpp/vLLM builds). Harmless if the local
            # server ignores this param — the prompt-side instruction to
            # "return only JSON" is what actually matters for those.
            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": pydantic_schema.__name__,
                    "schema": pydantic_schema.model_json_schema(),
                    "strict": True,
                },
            }

        try:
            response = await self.client.chat.completions.create(**request_kwargs)
        except Exception:
            logger.warning("LLM request failed", exc_info=True)
            return None

        choice = response.choices[0]
        content = (choice.message.content or "").strip()

        if not content:
            logger.warning(
                "Empty response from LLM (finish_reason=%r)",
                getattr(choice, "finish_reason", None),
            )
            return None

        # Strip ```json ... ``` fences some models add even when told not to.
        cleaned = _FENCE_PATTERN.sub("", content).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Model returned prose instead of JSON. Try to salvage a bare
            # 3-letter code (covers the IATA-lookup use case specifically);
            # otherwise give up and let the caller's fallback tier handle it.
            match = _IATA_FALLBACK_PATTERN.search(cleaned)
            if match and pydantic_schema is not None and "iata_code" in pydantic_schema.model_fields:
                logger.warning(
                    "Non-JSON response, extracted IATA via regex fallback: %s (raw: %r)",
                    match.group(1), cleaned[:200],
                )
                data = {"iata_code": match.group(1), "airport_name": cleaned}
            else:
                logger.warning("Non-JSON response from LLM: %r", cleaned[:200])
                return None

        if pydantic_schema is not None:
            try:
                return pydantic_schema.model_validate(data).model_dump()
            except Exception as e:
                logger.warning("Schema validation failed (%s) for data: %r", e, data)
                return None

        return data

    async def generate_text_response(self, prompt: str, **kwargs) -> str | None:
        """Like generate_response, but for free-text output (no JSON parsing).
        Use this when you want prose, not a structured object — e.g. the
        final polished itinerary write-up.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
        except Exception:
            logger.warning("LLM request failed", exc_info=True)
            return None

        content = (response.choices[0].message.content or "").strip()
        return content or None
        