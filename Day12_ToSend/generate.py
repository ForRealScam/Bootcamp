import json
import time
from openai import OpenAI

import config


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks with their source document and page number for the LLM prompt."""
    formatted_parts = []
    for idx, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "unknown")
        page = chunk.get("page", "?")
        content = chunk.get("content", "")
        formatted_parts.append(f"[{idx}] (Source: {source}, Page {page})\n{content}")
    return "\n\n".join(formatted_parts)


def generate_answer(query: str, chunks: list[dict]) -> dict:
    """Generate an answer to query using the retrieved chunks and the configured LLM."""
    context_used = format_context(chunks)
    system_prompt = config.SYSTEM_PROMPT.format(context=context_used)

    client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
    request_kwargs = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        "reasoning_effort": config.REASONING_EFFORT,
        config.TOKEN_LIMIT_PARAM: config.MAX_TOKENS,
    }
    if config.REASONING_EFFORT == "none":
        request_kwargs["temperature"] = config.TEMPERATURE

    start = time.time()
    response = client.chat.completions.create(**request_kwargs)
    elapsed_ms = round((time.time() - start) * 1000)

    choice = response.choices[0]
    usage = response.usage
    answer = (choice.message.content or "").strip()

    if not answer:
        print(
            f"WARNING: Empty answer generated for query='{query}'! "
            f"finish_reason='{choice.finish_reason}', model='{config.LLM_MODEL}'"
        )

    return {
        "query": query,
        "answer": answer,
        "context_used": context_used,
        "model": config.LLM_MODEL,
        "thinking": config.REASONING_EFFORT != "none",
        "finish_reason": choice.finish_reason,
        "generation_time_ms": elapsed_ms,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "tokens_generated": usage.completion_tokens if usage else None,
    }


if __name__ == "__main__":
    sample_chunks = [
        {
            "content": "Employees in eligible roles may work remotely for up to three (3) days per week, subject to manager approval.",
            "source": "company_handbook.pdf",
            "page": 4,
            "relevance_score": 0.85,
        }
    ]
    res = generate_answer("What is the maximum number of remote work days per week?", sample_chunks)
    print(json.dumps(res, indent=2, ensure_ascii=False))
