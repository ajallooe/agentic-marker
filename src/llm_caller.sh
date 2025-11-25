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
    local model="${MODEL}"

    # Build model argument if specified
    local model_arg=""
    if [[ -n "$model" ]]; then
        model_arg="--model $model"
    fi

    if [[ "$mode" == "interactive" ]]; then
        # Interactive mode - use stdin to provide initial prompt
        if [[ -n "$output" ]]; then
            # Use script to capture the session
            script -q "$output" bash -c "echo '$prompt' | claude $model_arg"
        else
            echo "$prompt" | claude $model_arg
        fi
    else
        # Headless mode - use --print for non-interactive output
        if [[ -n "$output" ]]; then
            claude --print $model_arg "$prompt" > "$output" 2>&1
        else
            claude --print $model_arg "$prompt"
        fi
    fi
}

# Function to call Gemini CLI
call_gemini() {
    local prompt="$1"
    local mode="$2"
    local output="$3"
    local model="${MODEL}"

    # Check if gemini CLI is available
    if ! command -v gemini &> /dev/null; then
        echo "Error: gemini CLI not found. Please install it first." >&2
        exit 1
    fi

    # Build model argument if specified
    local model_arg=""
    if [[ -n "$model" ]]; then
        model_arg="--model $model"
    fi

    if [[ "$mode" == "interactive" ]]; then
        # Interactive mode - use stdin to provide initial prompt
        if [[ -n "$output" ]]; then
            script -q "$output" bash -c "echo '$prompt' | gemini $model_arg"
        else
            echo "$prompt" | gemini $model_arg
        fi
    else
        # Headless mode - use positional prompt for one-shot execution
        if [[ -n "$output" ]]; then
            gemini $model_arg "$prompt" > "$output" 2>&1
        else
            gemini $model_arg "$prompt"
        fi
    fi
}

# Function to call Codex CLI
call_codex() {
    local prompt="$1"
    local mode="$2"
    local output="$3"
    local model="${MODEL}"

    # Check if codex CLI is available
    if ! command -v codex &> /dev/null; then
        echo "Error: codex CLI not found. Please install it first." >&2
        exit 1
    fi

    # Build model config if specified
    local model_arg=""
    if [[ -n "$model" ]]; then
        model_arg="-c model=$model"
    fi

    if [[ "$mode" == "interactive" ]]; then
        # Interactive mode - pass prompt as argument
        if [[ -n "$output" ]]; then
            # Use script to capture the session
            script -q "$output" bash -c "codex $model_arg '$prompt'"
        else
            codex $model_arg "$prompt"
        fi
    else
        # Headless mode - use 'exec' subcommand for non-interactive execution
        if [[ -n "$output" ]]; then
            codex exec $model_arg "$prompt" > "$output" 2>&1
        else
            codex exec $model_arg "$prompt"
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
        call_codex "$PROMPT" "$MODE" "$OUTPUT_FILE"
        ;;
    *)
        echo "Error: Unknown provider '$PROVIDER'. Supported: claude, gemini, codex" >&2
        exit 1
        ;;
esac

exit 0
