| Requirement | Status | Evidence |
|---|---|---|
| Browser prompt captured | PASS | browser_input.json |
| Backend request shape captured | PASS | backend_request_trace.json |
| Provider/model selection wiring captured | PASS | model_execution_trace.json |
| Generated output artifact created | PASS | generated_artifacts/src/App.jsx |
| Preview artifact created | PASS | preview.html |
| Deploy readiness linked | PASS | ../railway_verification/railway_readiness.json |
| Live LLM invocation | NOT RUN | Explicitly disabled in this deterministic harness |
| Live browser screenshot | NOT RUN | Requires supported Node/browser runtime |
