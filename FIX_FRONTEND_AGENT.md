# 🔥 CRITICAL FIX - Frontend Agent Output File Writing

## THE PROBLEM (Root Cause Analysis)

From the document you shared:

> **"Frontend step produced no output_files on disk"**

This means:
1. FrontendAgent IS being called ✅
2. FrontendAgent IS returning something
3. BUT files are NOT being written to disk ❌

## WHY IT'S FAILING (3 Possible Points)

### Issue 1: LLM Returns Raw Text (Not JSON)
- Prompt asks for JSON
- LLM returns explanation + JSON
- Parser fails to extract JSON
- `files` dict is empty
- No files written

### Issue 2: JSON Parsing Fails Silently
- Parser tries to extract JSON
- Fails and returns empty dict
- Executor logs but doesn't retry
- Returns empty result

### Issue 3: Files Dict Not Validated
- JSON is valid
- `files` key exists
- But is `None` or empty dict
- No exception raised
- Executor sees empty files

## THE FIXES (All 4 Must Be Applied)

### FIX 1: Enforce Strict JSON in Prompt
**File:** `backend/agents/frontend_agent.py`
**Line:** ~105

CHANGE FROM:
```text
Return ONLY valid JSON with this shape:
```

CHANGE TO:
```text
You MUST return ONLY a valid JSON object. No markdown. No explanations. ONLY JSON.

Start with { and end with }

{
  "files": { ... }
}
```

### FIX 2: Add Debug Logging in Agent
**File:** `backend/agents/frontend_agent.py`
**Line:** ~140 (before parse)

ADD:
```python
# DEBUG: Log raw response before parsing
logger.info(f"RAW LLM RESPONSE ({len(response)} chars): {response[:500]}...")

# Parse JSON response
data = self.parse_json_response(response)

# DEBUG: Log parsed result
logger.info(f"PARSED RESULT: files={len(data.get('files', {}))}, structure={bool(data.get('structure'))}")
```

### FIX 3: Add Explicit Validation in Agent
**File:** `backend/agents/frontend_agent.py`
**Line:** ~145 (after parse)

ADD:
```python
# EXPLICIT VALIDATION
if not data:
    raise AgentValidationError(f"{self.name}: parse_json_response returned empty result")

if not data.get("files"):
    raise AgentValidationError(f"{self.name}: No files in parsed JSON: {list(data.keys())}")

if not isinstance(data["files"], dict) or len(data["files"]) == 0:
    raise AgentValidationError(f"{self.name}: files is not a non-empty dict")
```

### FIX 4: Add Dump-to-Disk Validation in Executor
**File:** `backend/orchestration/executor.py`
**Line:** ~645 (after writing files)

ADD:
```python
# VALIDATION: Check files actually wrote
if out:
    logger.info(f"✅ Successfully wrote {len(out)} files")
    # Verify files exist
    for file_path in out:
        full_path = os.path.join(workspace_path, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            logger.info(f"   ✓ Verified: {file_path} ({size} bytes)")
        else:
            logger.error(f"   ✗ FILE NOT FOUND: {file_path}")
else:
    logger.error(f"❌ FrontendAgent wrote NO files to disk!")
    raise Exception("Frontend step produced no output_files on disk")
```

## TEST VERIFICATION

After applying all 4 fixes:

```bash
# Run test build
curl -X POST http://localhost:8000/api/build \
  -H "Content-Type: application/json" \
  -d '{"goal": "Simple button counter", ...}'
```

You MUST see:
- ✅ `RAW LLM RESPONSE` in logs
- ✅ `PARSED RESULT` shows files count > 0
- ✅ `Successfully wrote N files` message
- ✅ `Verified: file.jsx` messages
- ✅ Step 8/18 completes (moves to step 9)

## IF STILL FAILING

Check logs for:
1. `RAW LLM RESPONSE` - Is JSON present?
2. `PARSED RESULT` - Did parse_json_response work?
3. `files is not a non-empty dict` - What went wrong?
4. `FILE NOT FOUND` - Did _safe_write fail?

---

**DO NOT** proceed to other features until this is 100% fixed.

This is **THE** blocker.

