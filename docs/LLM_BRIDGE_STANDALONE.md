# LLM CLI Bridge - Standalone Usage Guide

A portable, future-proof shell script that provides a unified interface across Claude Code, Gemini CLI, and OpenAI Codex CLI. Designed to be dropped into any project for building agentic architectures.

## Quick Start

### 1. Copy the Bridge

Copy a single file to your project:

```bash
cp llm_caller.sh /path/to/your/project/
chmod +x /path/to/your/project/llm_caller.sh
```

That's it. The bridge has **zero dependencies** on other files.

### 2. Install at Least One CLI

| Provider | CLI | Installation |
|----------|-----|--------------|
| Anthropic | `claude` | https://claude.ai/code |
| Google | `gemini` | https://github.com/google-gemini/gemini-cli |
| OpenAI | `codex` | https://github.com/openai/codex |

### 3. Basic Usage

```bash
# Headless (non-interactive) - get a response and exit
./llm_caller.sh --provider claude --prompt "Explain recursion in one sentence" --mode headless

# Interactive - start a conversation
./llm_caller.sh --provider gemini --prompt "Help me refactor this codebase" --mode interactive
```

## Command Reference

```
Usage:
  llm_caller.sh --provider <claude|gemini|codex> --prompt "text" [OPTIONS]
  llm_caller.sh --config <config.yaml> --prompt "text" [OPTIONS]

Required (one of):
  --provider <name>       LLM provider: claude, gemini, or codex
  --config <file>         YAML config file with provider/model defaults

Prompt (one required):
  --prompt <text>         Prompt text
  --prompt-file <file>    Read prompt from file

Optional:
  --model <name>          Model to use (passed directly to CLI)
  --mode <mode>           interactive or headless (default: interactive)
  --output <file>         Capture output to file
  --working-dir <dir>     Set working directory for file operations
  --auto-approve          Skip all permission prompts (use with caution)
  --write-dirs <dirs>     Space-separated list of directories to allow writes
  --help                  Show help message
```

## Configuration File

Instead of passing `--provider` every time, create a config file:

```yaml
# llm_config.yaml
default_provider: claude
default_model: claude-sonnet-4

# Or per-provider defaults:
providers:
  claude:
    model: claude-sonnet-4
  gemini:
    model: gemini-2.5-pro
  codex:
    model: gpt-4o
```

Then use it:

```bash
./llm_caller.sh --config llm_config.yaml --prompt "Hello"
```

Command-line arguments override config file values.

## Integration Patterns

### Pattern 1: Direct Shell Integration

For shell scripts that need LLM capabilities:

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLM="$SCRIPT_DIR/llm_caller.sh"

# Get a response
response=$("$LLM" --provider claude --prompt "Summarize: $1" --mode headless)
echo "Summary: $response"
```

### Pattern 2: Python Subprocess

For Python agents that need LLM calls:

```python
import subprocess
from pathlib import Path

def call_llm(prompt: str, provider: str = "claude", model: str = None) -> str:
    """Call the LLM bridge and return the response."""
    cmd = [
        str(Path(__file__).parent / "llm_caller.sh"),
        "--provider", provider,
        "--prompt", prompt,
        "--mode", "headless",
        "--auto-approve"
    ]
    if model:
        cmd.extend(["--model", model])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"LLM call failed: {result.stderr}")

    return result.stdout.strip()

# Usage
response = call_llm("What is 2+2?")
print(response)  # "4"
```

### Pattern 3: Multi-Agent System

For systems with multiple specialized agents:

```python
from pathlib import Path
import subprocess

class Agent:
    def __init__(self, name: str, system_prompt: str, provider: str = "claude"):
        self.name = name
        self.system_prompt = system_prompt
        self.provider = provider
        self.llm_caller = Path(__file__).parent / "llm_caller.sh"

    def run(self, task: str, interactive: bool = False) -> str:
        prompt = f"{self.system_prompt}\n\nTask: {task}"

        cmd = [
            str(self.llm_caller),
            "--provider", self.provider,
            "--prompt", prompt,
            "--mode", "interactive" if interactive else "headless",
            "--auto-approve"
        ]

        if interactive:
            # For interactive, inherit stdio
            subprocess.run(cmd)
            return ""
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.strip()

# Define specialized agents
researcher = Agent(
    name="Researcher",
    system_prompt="You are a research assistant. Analyze information thoroughly.",
    provider="claude"
)

coder = Agent(
    name="Coder",
    system_prompt="You are an expert programmer. Write clean, efficient code.",
    provider="codex"
)

# Use them
analysis = researcher.run("Analyze the pros and cons of microservices")
code = coder.run("Write a Python function to parse JSON safely")
```

### Pattern 4: Prompt Templates

For reusable prompt patterns:

```python
def create_analysis_prompt(content: str, focus: str) -> str:
    return f"""Analyze the following content with a focus on {focus}.

Content:
{content}

Provide:
1. Key findings
2. Potential issues
3. Recommendations
"""

def analyze(content: str, focus: str, provider: str = "claude") -> str:
    prompt = create_analysis_prompt(content, focus)
    return call_llm(prompt, provider=provider)
```

### Pattern 5: With Config File

For projects with consistent defaults:

```python
from pathlib import Path
import subprocess

class LLMBridge:
    def __init__(self, config_path: str = None):
        self.llm_caller = Path(__file__).parent / "llm_caller.sh"
        self.config_path = config_path

    def call(self, prompt: str, provider: str = None, model: str = None,
             mode: str = "headless", auto_approve: bool = True) -> str:

        cmd = [str(self.llm_caller)]

        if self.config_path:
            cmd.extend(["--config", self.config_path])
        if provider:
            cmd.extend(["--provider", provider])
        if model:
            cmd.extend(["--model", model])

        cmd.extend([
            "--prompt", prompt,
            "--mode", mode
        ])

        if auto_approve:
            cmd.append("--auto-approve")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"LLM call failed: {result.stderr}")

        return result.stdout.strip()

# Usage with config
bridge = LLMBridge(config_path="llm_config.yaml")
response = bridge.call("Hello!")  # Uses defaults from config
```

## Execution Modes

### Headless Mode (`--mode headless`)

- Non-interactive, returns immediately with response
- Best for automated pipelines, batch processing, API-like usage
- Output goes to stdout (capture with subprocess or redirect)

```bash
# Capture to variable
result=$(./llm_caller.sh --provider claude --prompt "Say OK" --mode headless)

# Capture to file
./llm_caller.sh --provider claude --prompt "Generate report" --mode headless > report.txt
```

### Interactive Mode (`--mode interactive`)

- Full conversational interface
- User can continue the conversation
- Best for complex tasks requiring back-and-forth

```bash
# Start interactive session
./llm_caller.sh --provider claude --prompt "Help me debug this issue" --mode interactive
```

## Auto-Approve Flag

The `--auto-approve` flag bypasses permission prompts:

| Provider | Effect |
|----------|--------|
| Claude | Uses `--dangerously-skip-permissions` |
| Gemini | Uses `--yolo` mode |
| Codex | Uses `--dangerously-bypass-approvals-and-sandbox` |

**Use with caution** - only in trusted environments or sandboxed containers.

## Provider-Specific Notes

### Claude Code
- Interactive mode provides full agentic capabilities (file read/write, bash)
- Headless mode uses `--print` flag
- Default allowed tools: Read, Write, Edit, Bash

### Gemini CLI
- Interactive mode uses `-i` flag
- Headless mode uses `-p` flag
- Use `--write-dirs` to grant directory access

### Codex CLI
- Interactive mode is full TUI
- Headless mode uses `codex exec` subcommand
- Has built-in sandboxing with `workspace-write` policy

## Error Handling

The bridge exits with non-zero status on errors:

```python
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    # Check stderr for error details
    if "not found" in result.stderr:
        print("CLI tool not installed")
    elif "rate limit" in result.stderr.lower():
        print("API rate limited, retry later")
    else:
        print(f"Error: {result.stderr}")
```

## Project Structure Example

```
my-agentic-project/
├── llm_caller.sh          # The bridge (copy this)
├── llm_config.yaml        # Your config (optional)
├── agents/
│   ├── researcher.py
│   ├── coder.py
│   └── reviewer.py
├── prompts/
│   ├── research.md
│   └── code_review.md
└── main.py
```

## Future-Proofing

The bridge is designed to be future-proof:

1. **No hardcoded model names** - Models are passed through without validation
2. **No hardcoded defaults** - All defaults come from config or CLI
3. **Provider abstraction** - Adding new providers requires only adding a new `call_<provider>` function
4. **CLI version agnostic** - Uses stable CLI flags that are unlikely to change

When new models are released, simply use them:

```bash
./llm_caller.sh --provider claude --model claude-5-opus --prompt "Hello"
```

No bridge updates required.

## License

This bridge script is provided as-is for use in any project.
