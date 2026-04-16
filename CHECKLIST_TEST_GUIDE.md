# CrucibAI Test Checklist - Brain Layer Validation
**Goal**: Verify CrucibAI feels like ONE intelligent builder for both nobuilders and builders.

## Test Prompts (Run in /crucib_brain_layer_test.ipynb)

### 1. Nobuilder Test: "Build me a stunning multi-page website"
**Expected Behavior**:
- ✓ Brain understands it's a full web project
- ✓ Selects FrontendAgent, DesignAgent, ContentAgent
- ✓ Generates actual HTML/CSS/JS files
- ✓ Creates coherent site structure
- ✓ Explains decisions clearly
- ✓ User feels one system handled it

**Validation**: User can open generated files and see working website

### 2. Builder Test: "Integrate Stripe payments and auth with role-based access"
**Expected Behavior**:
- ✓ Brain understands complex backend task
- ✓ Selects BackendAgent, SecurityAgent, DatabaseAgent, PaymentsAgent
- ✓ Generates API code, database schema, auth flow
- ✓ Creates configuration guidelines
- ✓ Explains architecture & security considerations
- ✓ User learns something new

**Validation**: Generated code is production-ready, secure, explains reasoning

### 3. Adaptation Test: "Actually, add AI chat to the website"
**Expected Behavior**:
- ✓ Brain understands it's expanding the previous request
- ✓ Dynamically escalates to add AIAgent, APIAgent
- ✓ Generates chat component + backend integration
- ✓ Integrates with existing structure seamlessly
- ✓ Feels like one conversation continuing
- ✓ No agent chaos visible

**Validation**: New feature integrates smoothly, conversation feels natural

### 4. Recovery Test: "The auth endpoint is failing, fix it"
**Expected Behavior**:
- ✓ Brain understands it's a fix/debugging task
- ✓ Selects DebugAgent, SecurityAgent (not all agents)
- ✓ Identifies root cause
- ✓ Provides targeted fix
- ✓ Explains what went wrong and why
- ✓ User successfully applies fix

**Validation**: Fix is accurate, targeted, educational

### 5. Deep Dive Test: "Explain the architecture you built"
**Expected Behavior**:
- ✓ Brain summarizes decisions from previous requests
- ✓ Explains interconnections
- ✓ Justifies architectural choices
- ✓ Provides diagrams/code references
- ✓ Feels authoritative, coherent
- ✓ User understands full system

**Validation**: Explanation is comprehensive, accurate, actionable

## Checklist Criteria (All Must Pass)

### Brain Layer Capabilities
- [ ] **Understands requests** - Semantic routing works
- [ ] **Plans approach** - Assessment generates coherent plans
- [ ] **Selects agents** - Uses minimum necessary, not all
- [ ] **Executes real work** - Actually generates code/files, not fake
- [ ] **Returns coherent result** - One unified output, no agent noise
- [ ] **Explains reasoning** - Why these agents, why this approach
- [ ] **Adapts to changes** - Dynamic escalation works
- [ ] **Continues conversation** - Session context preserved

### UX Quality
- [ ] **Feels like one builder** - Not visible agent swaps
- [ ] **Calm, clear progress** - Streaming updates coherent
- [ ] **No chaos visible** - Agent conflicts hidden
- [ ] **Trust-worthy** - Explanations match actual output
- [ ] **Learns from context** - Builds on previous requests
- [ ] **Professional output** - Fortune 100 quality
- [ ] **Actionable** - User can use/deploy generated code

### Output Quality (Code/Files)
- [ ] **Syntax correct** - Compiles/runs without errors
- [ ] **Best practices** - Follows industry standards
- [ ] **Well-documented** - Comments explain complexity
- [ ] **Production-ready** - Not toy examples
- [ ] **Secure** - No obvious vulnerabilities
- [ ] **Performant** - Reasonable efficiency
- [ ] **Tested** - Includes test cases where appropriate
- [ ] **Integrated** - Connects to other generated components

## Success Criteria

### Minimum (Validate "One Builder")
- ✓ At least 3 test prompts run successfully
- ✓ Generated code/files are real (not placeholders)
- ✓ Output quality is professional
- ✓ User experience feels coherent (not agent chaos)

### Target (Confirm "Number 1" Status)
- ✓ All 5 test prompts pass
- ✓ Brain dynamics escalation works (test 3)
- ✓ Recovery routing works (test 4)
- ✓ Output rivals top AI builders
- ✓ Architecture explanation (test 5) is authoritative

### Excellence (Future)
- ✓ Multi-request conversations feel natural
- ✓ Agent selection is always optimal
- ✓ Streaming UX is indistinguishable from single agent
- ✓ Reasoning transparency is exceptional
- ✓ Output is indistinguishable from human expert

## How to Run Tests

1. **Set up local environment**:
   ```bash
   docker compose up -d postgres redis
   cd crucib/backend
   python -m uvicorn server:app --reload
   ```

2. **Open notebook**:
   - Navigate to `crucib_brain_layer_test.ipynb`
   - Run each test cell in sequence
   - Observe brain layer behavior

3. **Validate outputs**:
   - Check generated files/code
   - Run generated code if applicable
   - Verify quality against criteria above

4. **Document results**:
   - Note which tests passed/failed
   - Save output samples
   - Document any agent selection issues

## Known Blockers
- Local database setup required (PostgreSQL + Redis)
- Node version must be 18-22 for frontend (if testing UI)
- LLM keys (Cerebras/Anthropic) needed for agent execution

## Files to Reference
- `backend/services/brain_layer.py` - Core implementation
- `crucib_brain_layer_test.ipynb` - Test runner
- `backend/test_brain_layer.py` - Unit tests
- `BRAIN_LAYER_PROGRESS.md` - Detailed progress
