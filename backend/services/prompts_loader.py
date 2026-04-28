import os

def load_prompt(filename: str) -> str:
    """Load a system prompt from the prompts directory."""
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
