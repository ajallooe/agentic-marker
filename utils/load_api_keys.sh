#!/usr/bin/env bash
#
# Load API keys from .secrets/ directory into environment variables
#
# Usage:
#   source utils/load_api_keys.sh     # from project root
#   source load_api_keys.sh           # from utils/ directory
#
# NOTE: This file must be SOURCED, not executed, for the exports to persist.
# Sourcing runs it in your current shell so exports are available afterward.
#

# Find project root by looking for .secrets/ directory
# First try current directory, then parent of script location
if [[ -d ".secrets" ]]; then
    PROJECT_ROOT="$(pwd)"
elif [[ -d "$(dirname "$0")/../.secrets" ]]; then
    PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
else
    # Last resort: check common locations
    for dir in "." ".." "../.."; do
        if [[ -d "$dir/.secrets" ]]; then
            PROJECT_ROOT="$(cd "$dir" && pwd)"
            break
        fi
    done
fi

SECRETS_DIR="$PROJECT_ROOT/.secrets"

if [[ ! -d "$SECRETS_DIR" ]]; then
    echo "Warning: .secrets/ directory not found at $SECRETS_DIR"
    return 1 2>/dev/null || exit 1
fi

# Load Claude API key (Anthropic)
if [[ -f "$SECRETS_DIR/CLAUDE_API_KEY" ]]; then
    export CLAUDE_API_KEY="$(cat "$SECRETS_DIR/CLAUDE_API_KEY" | tr -d '\n')"
    export ANTHROPIC_API_KEY="$CLAUDE_API_KEY"  # Alias for SDK compatibility
    echo "Loaded CLAUDE_API_KEY (also set as ANTHROPIC_API_KEY)"
elif [[ -f "$SECRETS_DIR/ANTHROPIC_API_KEY" ]]; then
    # Backward compatibility
    export ANTHROPIC_API_KEY="$(cat "$SECRETS_DIR/ANTHROPIC_API_KEY" | tr -d '\n')"
    export CLAUDE_API_KEY="$ANTHROPIC_API_KEY"
    echo "Loaded ANTHROPIC_API_KEY (also set as CLAUDE_API_KEY)"
fi

# Load Google/Gemini API key
if [[ -f "$SECRETS_DIR/GEMINI_API_KEY" ]]; then
    export GEMINI_API_KEY="$(cat "$SECRETS_DIR/GEMINI_API_KEY" | tr -d '\n')"
    export GOOGLE_API_KEY="$GEMINI_API_KEY"  # Alias for compatibility
    echo "Loaded GEMINI_API_KEY (also set as GOOGLE_API_KEY)"
elif [[ -f "$SECRETS_DIR/GOOGLE_API_KEY" ]]; then
    export GOOGLE_API_KEY="$(cat "$SECRETS_DIR/GOOGLE_API_KEY" | tr -d '\n')"
    export GEMINI_API_KEY="$GOOGLE_API_KEY"  # Alias for compatibility
    echo "Loaded GOOGLE_API_KEY (also set as GEMINI_API_KEY)"
fi

# Load OpenAI API key
if [[ -f "$SECRETS_DIR/OPENAI_API_KEY" ]]; then
    export OPENAI_API_KEY="$(cat "$SECRETS_DIR/OPENAI_API_KEY" | tr -d '\n')"
    echo "Loaded OPENAI_API_KEY"
fi

echo "API keys loaded from $SECRETS_DIR"
