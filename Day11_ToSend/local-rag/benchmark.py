import json
import time
from openai import OpenAI

MODELS = ["qwen3.5:4b-q4_K_M", "qwen3.5:2b-q4_K_M"]
BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
REASONING_EFFORT = "none"

PROMPTS = [
    {
        "category": "factual",
        "prompt": "What causes tides on Earth? Answer in 2-3 sentences.",
    },
    {
        "category": "reasoning",
        "prompt": (
            "If a train travels 120km in 1.5 hours, and then 80km in 1 hour, "
            "what is the average speed for the entire journey? Show your calculation briefly."
        ),
    },
    {
        "category": "summarization",
        "prompt": (
            "Summarize the following paragraph in one concise sentence:\n\n"
            "Retrieval-Augmented Generation (RAG) is an architectural approach that improves the efficacy "
            "of large language model applications by leveraging custom data. This is done by retrieving "
            "data or documents relevant to a question or task and providing them as context for the LLM. "
            "RAG has shown success in support chatbots and Q&A systems that need to maintain up-to-date "
            "information or access domain-specific knowledge without retraining the underlying model."
        ),
    },
    {
        "category": "structured",
        "prompt": 'List 3 European capitals. Respond ONLY with valid JSON: [{"city": ..., "country": ...}]',
    },
    {
        "category": "code_generation",
        "prompt": (
            "Write a Python function `merge_sorted_lists(a: list[int], b: list[int]) -> list[int]` "
            "that merges two already-sorted lists into a single sorted list in O(n + m) time "
            "without using `sorted()` or `.sort()`. Include a brief docstring."
        ),
    },
    {
        "category": "instruction_following",
        "prompt": (
            "Explain why regulated companies use local LLMs instead of cloud APIs. "
            "Format your response as exactly 3 bullet points, where each bullet point starts with `- **`, "
            "and keep the entire response under 60 words."
        ),
    },
]


def warmup_model(client: OpenAI, model: str) -> None:
    """Load the model into memory before timing benchmark prompts."""
    print(f"Warming up {model}...")
    client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hi"}],
        reasoning_effort=REASONING_EFFORT,
        max_tokens=5,
    )


def run_benchmark(model: str, prompt_item: dict) -> dict:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_item["prompt"]}],
        temperature=0.7,
        reasoning_effort=REASONING_EFFORT,
        max_tokens=1024,
    )
    elapsed = time.time() - start
    choice = response.choices[0]
    usage = response.usage
    content = choice.message.content or ""

    if not content.strip():
        print(
            f"WARNING: Empty response for model={model}, category={prompt_item['category']}, "
            f"finish_reason={choice.finish_reason}"
        )

    return {
        "model": model,
        "category": prompt_item["category"],
        "prompt": prompt_item["prompt"],
        "response": content,
        "thinking": REASONING_EFFORT != "none",
        "finish_reason": choice.finish_reason,
        "time_seconds": round(elapsed, 2),
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "tokens_per_second": (
            round(usage.completion_tokens / elapsed, 1)
            if usage and usage.completion_tokens and elapsed > 0
            else None
        ),
        "quality_rating": None,
        "rating_note": "",
    }


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    results = []

    for model in MODELS:
        warmup_model(client, model)
        for prompt_item in PROMPTS:
            print(f"Running [{model}] -> {prompt_item['category']}...")
            res = run_benchmark(model, prompt_item)
            print(
                f"  Done in {res['time_seconds']}s | "
                f"{res['completion_tokens']} tokens | "
                f"{res['tokens_per_second']} tok/s | "
                f"finish_reason={res['finish_reason']}"
            )
            results.append(res)

    output_path = "benchmark_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(results)} benchmark results to {output_path}")


if __name__ == "__main__":
    main()
