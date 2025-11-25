#!/usr/bin/env bash
#
# Unified LLM Caller - Routes to appropriate CLI tool
# Usage: llm_caller.sh --prompt "text" [--mode interactive|headless] [--provider claude|gemini|openai] [--model model_name] [--output file]
#

set -euo pipefail

# Default values
MODE="interactive"
PROVIDER=""
MODEL=""
PROMPT=""
OUTPUT_FILE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)
            PROMPT="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Validate prompt is provided
if [[ -z "$PROMPT" ]]; then
    echo "Error: --prompt is required" >&2
    exit 1
fi

# Infer provider from model if not specified
if [[ -z "$PROVIDER" && -n "$MODEL" ]]; then
    if [[ "$MODEL" == claude-* ]]; then
        PROVIDER="claude"
    elif [[ "$MODEL" == gemini-* ]]; then
        PROVIDER="gemini"
    elif [[ "$MODEL" == gpt-* ]]; then
        PROVIDER="openai"
    fi
fi

# Default to claude if still not specified
if [[ -z "$PROVIDER" ]]; then
    PROVIDER="claude"
fi

# Function to call Claude Code CLI
call_claude() {
    local prompt="$1"
    local mode="$2"
    local output="$3"

    if [[ "$mode" == "interactive" ]]; then
        # Interactive mode with session capture
        if [[ -n "$output" ]]; then
            # Use script to capture the session
            script -q "$output" bash -c "echo '$prompt' | claude"
        else
            echo "$prompt" | claude
        fi
    else
        # Headless mode - use claude with piped input and capture output
        # Note: Claude Code may not have a pure headless mode, so we simulate it
        if [[ -n "$output" ]]; then
            # Create a temporary expect script to automate the interaction
            local temp_expect=$(mktemp)
            cat > "$temp_expect" <<EOF
#!/usr/bin/env expect -f
set timeout -1
spawn claude
expect ">"
send "$prompt\r"
expect ">"
send "/exit\r"
expect eof
EOF
            chmod +x "$temp_expect"
            "$temp_expect" > "$output" 2>&1
            rm "$temp_expect"
        else
            echo "Warning: Headless mode without output file not fully supported for Claude" >&2
            echo "$prompt" | claude
        fi
    fi
}

# Function to call Gemini CLI
call_gemini() {
    local prompt="$1"
    local mode="$2"
    local output="$3"
    local model="${MODEL:-gemini-pro}"

    # Check if gemini CLI is available
    if ! command -v gemini &> /dev/null; then
        echo "Error: gemini CLI not found. Please install it first." >&2
        echo "You may need to install: pip install google-generativeai-cli or similar" >&2
        exit 1
    fi

    if [[ "$mode" == "interactive" ]]; then
        if [[ -n "$output" ]]; then
            script -q "$output" bash -c "gemini chat --model '$model' <<< '$prompt'"
        else
            gemini chat --model "$model" <<< "$prompt"
        fi
    else
        # Headless mode
        if [[ -n "$output" ]]; then
            gemini generate --model "$model" "$prompt" > "$output" 2>&1
        else
            gemini generate --model "$model" "$prompt"
        fi
    fi
}

# Function to call OpenAI CLI (Codex)
call_openai() {
    local prompt="$1"
    local mode="$2"
    local output="$3"
    local model="${MODEL:-gpt-4}"

    # Check if openai CLI is available
    if ! command -v openai &> /dev/null; then
        echo "Error: openai CLI not found. Please install it first." >&2
        echo "Install with: pip install openai-cli or similar" >&2
        exit 1
    fi

    if [[ "$mode" == "interactive" ]]; then
        if [[ -n "$output" ]]; then
            script -q "$output" bash -c "openai chat --model '$model' <<< '$prompt'"
        else
            openai chat --model "$model" <<< "$prompt"
        fi
    else
        # Headless mode
        if [[ -n "$output" ]]; then
            openai complete --model "$model" "$prompt" > "$output" 2>&1
        else
            openai complete --model "$model" "$prompt"
        fi
    fi
}

# Route to appropriate provider
case "$PROVIDER" in
    claude)
        call_claude "$PROMPT" "$MODE" "$OUTPUT_FILE"
        ;;
    gemini)
        call_gemini "$PROMPT" "$MODE" "$OUTPUT_FILE"
        ;;
    openai|codex)
        call_openai "$PROMPT" "$MODE" "$OUTPUT_FILE"
        ;;
    *)
        echo "Error: Unknown provider '$PROVIDER'. Supported: claude, gemini, openai" >&2
        exit 1
        ;;
esac

exit 0
