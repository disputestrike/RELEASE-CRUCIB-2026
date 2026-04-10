from agent_real_behavior import _extract_code_or_text
from real_agent_runner import _extract_code


def test_extract_code_prefers_matching_fenced_block_for_jsx():
    raw = """Here is your component.

```json
{"name":"wrong"}
```

```jsx
export default function App() {
  return <div>Hello</div>;
}
```
"""

    cleaned = _extract_code(raw, filepath="src/App.jsx")

    assert "export default function App()" in cleaned
    assert "```" not in cleaned
    assert '{"name":"wrong"}' not in cleaned


def test_extract_code_or_text_removes_fence_lines_and_prose():
    raw = """I appreciate the requirements.
```jsx
export default function App() {
  return <div>Hello</div>;
}
```
"""

    cleaned = _extract_code_or_text(raw, filepath="src/App.jsx")

    assert cleaned.lstrip().startswith("export default function App()")
    assert "```" not in cleaned
