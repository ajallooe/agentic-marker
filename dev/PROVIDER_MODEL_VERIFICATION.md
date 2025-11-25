# Provider/Model Configuration Verification

This document verifies that provider and model configuration flows correctly through the entire workflow.

## Configuration Chain

### 1. Configuration Source: `overview.md`

```yaml
default_provider: codex
default_model: gpt-5.1
```

### 2. Orchestration Scripts Load Configuration

**mark_structured.sh** (line 102):
```bash
eval "$("$SRC_DIR/utils/config_parser.py" "$OVERVIEW_FILE" --bash)"
# Sets: $DEFAULT_PROVIDER and $DEFAULT_MODEL
```

**mark_freeform.sh** (line 102):
```bash
eval "$("$SRC_DIR/utils/config_parser.py" "$OVERVIEW_FILE" --bash)"
# Sets: $DEFAULT_PROVIDER and $DEFAULT_MODEL
```

### 3. All Agent Invocations Receive Provider/Model

#### mark_structured.sh

| Agent | Line | Provider | Model |
|-------|------|----------|-------|
| pattern_designer.py | 204-211 | ✓ Line 209 | ✓ Line 210 |
| marker.py | 248 | ✓ | ✓ |
| normalizer.py | N/A (TODO) | N/A | N/A |
| unifier.py | 362 | ✓ | ✓ |
| aggregator.py | 409-417 | ✓ Line 414 | ✓ Line 415 |

#### mark_freeform.sh

| Agent | Line | Provider | Model |
|-------|------|----------|-------|
| pattern_designer.py | 175-181 | ✓ Line 179 | ✓ Line 180 |
| marker.py | 223 | ✓ | ✓ |
| normalizer.py | 269-275 | ✓ Line 273 | ✓ Line 274 |
| unifier.py | 339 | ✓ | ✓ |
| aggregator.py | 386-394 | ✓ Line 391 | ✓ Line 392 |

### 4. All Agents Accept Provider/Model Arguments

**Verified in:**
- `src/agents/marker.py` (lines 120-127)
- `src/agents/unifier.py` (lines 95-102)
- `src/agents/normalizer.py` (lines 95-102)
- `src/agents/pattern_designer.py` (lines 101-108)
- `src/agents/aggregator.py` (lines 88-95)

All agents have:
```python
parser.add_argument("--provider", default="claude", help="LLM provider")
parser.add_argument("--model", help="LLM model")
```

**Note:** All have `default="claude"` fallback if not provided.

### 5. All Agents Pass to llm_caller.sh

**Verified pattern in all agents:**
```python
llm_caller = Path(__file__).parent.parent / "llm_caller.sh"

cmd = [
    str(llm_caller),
    "--prompt", prompt,
    "--mode", "headless",  # or "interactive"
    "--provider", args.provider,  # ✓
    "--output", args.output
]

if args.model:
    cmd.extend(["--model", args.model])  # ✓

result = subprocess.run(cmd, capture_output=True, text=True)
```

**Verified in:**
- marker.py (lines 171-184)
- unifier.py (lines 171-184)
- normalizer.py (lines 145-158)
- pattern_designer.py (lines 166-179)
- aggregator.py (lines 161-174)

### 6. llm_caller.sh Routes to Correct Provider

**src/llm_caller.sh** (lines 184-198):
```bash
case "$PROVIDER" in
    claude)
        call_claude "$PROMPT" "$MODE" "$OUTPUT_FILE"  # ✓
        ;;
    gemini)
        call_gemini "$PROMPT" "$MODE" "$OUTPUT_FILE"  # ✓
        ;;
    openai|codex)
        call_codex "$PROMPT" "$MODE" "$OUTPUT_FILE"   # ✓
        ;;
    *)
        echo "Error: Unknown provider '$PROVIDER'" >&2
        exit 1
        ;;
esac
```

### 7. Provider Functions Use Model

**call_claude()** (lines 69-98):
```bash
local model="${MODEL}"  # Line 74 ✓
local model_arg=""
if [[ -n "$model" ]]; then
    model_arg="--model $model"  # Line 79 ✓
fi
claude --print --permission-mode bypassPermissions $model_arg "$prompt"  # Line 94 ✓
```

**call_gemini()** (lines 101-137):
```bash
local model="${MODEL}"  # Line 106 ✓
local model_arg=""
if [[ -n "$model" ]]; then
    model_arg="--model $model"  # Line 117 ✓
fi
gemini --yolo $model_arg "$prompt"  # Line 132 ✓
```

**call_codex()** (lines 139-181):
```bash
local model="${MODEL}"  # Line 144 ✓
local model_arg=""
if [[ -n "$model" ]]; then
    model_arg="-c model=$model"  # Line 155 ✓
fi
codex exec --sandbox workspace-write $model_arg "$prompt"  # Line 176 ✓
```

## Complete Flow Example

### User Configuration
```yaml
# assignments/lab1/overview.md
default_provider: codex
default_model: gpt-5.1
```

### Execution Trace

1. **Script loads config:**
   ```bash
   DEFAULT_PROVIDER="codex"
   DEFAULT_MODEL="gpt-5.1"
   ```

2. **Script generates marker task:**
   ```bash
   python3 marker.py --activity A1 --student 'John' \
     --submission '/path/to/notebook.ipynb' \
     --output 'markings/John_A1.md' \
     --provider 'codex' \
     --model 'gpt-5.1'
   ```

3. **marker.py receives:**
   ```python
   args.provider = "codex"
   args.model = "gpt-5.1"
   ```

4. **marker.py calls llm_caller.sh:**
   ```bash
   llm_caller.sh --prompt "..." --mode "headless" \
     --provider "codex" --model "gpt-5.1" \
     --output "markings/John_A1.md"
   ```

5. **llm_caller.sh routes:**
   ```bash
   PROVIDER="codex"
   MODEL="gpt-5.1"
   call_codex "$PROMPT" "$MODE" "$OUTPUT_FILE"
   ```

6. **call_codex executes:**
   ```bash
   codex exec --sandbox workspace-write -c model=gpt-5.1 "$prompt"
   ```

## Verification Status

✅ **Configuration Loading:** Verified
✅ **Pattern Designer:** Receives provider/model in all scripts
✅ **Marker Agent:** Fixed - now receives provider/model
✅ **Normalizer Agent:** Receives provider/model (freeform only)
✅ **Unifier Agent:** Fixed - now receives provider/model
✅ **Aggregator Agent:** Receives provider/model in all scripts

✅ **All agents accept arguments:** Verified
✅ **All agents pass to llm_caller.sh:** Verified
✅ **llm_caller.sh routes correctly:** Verified
✅ **Provider functions use model:** Verified

## Bug That Was Fixed

**Before fix:**
- Marker and unifier task commands did NOT include `--provider` or `--model`
- Agents used their hardcoded `default="claude"`
- User's configuration was ignored

**After fix:**
- All task commands include `--provider '$DEFAULT_PROVIDER'` and `--model '$DEFAULT_MODEL'`
- Configuration from overview.md is respected
- Correct provider and model used throughout

## Testing Recommendation

To verify the fix works:

1. Set `default_provider: codex` and `default_model: gpt-5.1` in overview.md
2. Generate tasks: `./mark_structured.sh assignments/test --no-resume`
3. Check generated task file: `cat processed/marker_tasks.txt | head -1`
4. Should see: `--provider 'codex' --model 'gpt-5.1'`
5. When tasks run, check output files for Codex-specific messages (not Claude)

## Files Modified

- mark_structured.sh (lines 248, 362)
- mark_freeform.sh (lines 223, 339)

All other agent invocations already had provider/model arguments.
