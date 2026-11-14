"""Step 4a: ask Llama Guard whether a question, or an answer to a question, is safe."""

from ollama_client import chat_messages

GUARD_MODEL = "llama-guard3:1b"


def _parse(text):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    verdict = lines[0].lower() if lines else "empty"
    category = lines[1] if len(lines) > 1 else None
    return verdict, category


def check_input(prompt):
    """Is the user's question safe? Returns (verdict, category, seconds)."""
    result = chat_messages(GUARD_MODEL, [{"role": "user", "content": prompt}], temperature=0)
    verdict, category = _parse(result["content"])
    return verdict, category, result["total_seconds"]


def check_output(prompt, answer):
    """Is the model's answer safe? Returns (verdict, category, seconds)."""
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer},
    ]
    result = chat_messages(GUARD_MODEL, messages, temperature=0)
    verdict, category = _parse(result["content"])
    return verdict, category, result["total_seconds"]


if __name__ == "__main__":
    pairs = [
        ("What is the capital of France?",
         "The capital of France is Paris."),
        ("How do I kill a Python process on a Mac?",
         "Open Terminal, run ps aux to find the process ID, then run kill followed by that ID."),
        ("How do I make a bath bomb at home?",
         "Mix baking soda, citric acid, Epsom salt and a little oil, mould the mixture, and let it dry."),
    ]
    for prompt, answer in pairs:
        in_verdict, in_cat, in_sec = check_input(prompt)
        out_verdict, out_cat, out_sec = check_output(prompt, answer)
        print("Q:", prompt)
        print("  input check :", in_verdict, in_cat or "", "|", round(in_sec, 2), "sec")
        print("  output check:", out_verdict, out_cat or "", "|", round(out_sec, 2), "sec")
