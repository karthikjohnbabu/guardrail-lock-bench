"""Send questions to a local Ollama model."""

import json
import urllib.error
import urllib.request

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


def chat_messages(model, messages, temperature=0.7, think=None, timeout=600):
    """Send a full list of messages and return the answer plus timings.

    think=None  -> do not send the setting (for models that cannot think)
    think=False -> ask a thinking model not to think
    """
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if think is not None:
        body["think"] = think

    request = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError("Ollama returned an error: " + detail)
    except urllib.error.URLError:
        raise RuntimeError("Cannot reach Ollama. Is it running? Try: brew services start ollama")

    message = data.get("message", {})
    eval_count = data.get("eval_count", 0)
    eval_seconds = data.get("eval_duration", 0) / 1e9
    tokens_per_sec = eval_count / eval_seconds if eval_seconds > 0 else None

    return {
        "content": message.get("content", ""),
        "thinking": message.get("thinking", ""),
        "total_seconds": data.get("total_duration", 0) / 1e9,
        "load_seconds": data.get("load_duration", 0) / 1e9,
        "output_tokens": eval_count,
        "tokens_per_sec": tokens_per_sec,
    }


def chat(model, user_prompt, system_prompt=None, temperature=0.7, think=None, timeout=600):
    """Ask one question, with an optional system prompt."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return chat_messages(model, messages, temperature=temperature, think=think, timeout=timeout)


if __name__ == "__main__":
    import sys

    model = sys.argv[1]
    prompt = sys.argv[2]
    think = False if "--nothink" in sys.argv else None

    result = chat(model, prompt, think=think)

    print("Answer starts :", result["content"][:300].replace("\n", " "))
    print("Thinking text :", "yes" if result["thinking"] else "no")
    print("Model load sec:", round(result["load_seconds"], 2))
    print("Total seconds :", round(result["total_seconds"], 2))
    print("Output tokens :", result["output_tokens"])
    if result["tokens_per_sec"]:
        print("Tokens per sec:", round(result["tokens_per_sec"], 1))
