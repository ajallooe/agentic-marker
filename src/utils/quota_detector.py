#!/usr/bin/env python3
"""
Quota/Rate Limit Detection Utility

Detects when LLM API calls fail due to quota or rate limit exhaustion
and provides clear, actionable warnings to instructors.
"""

import sys


def is_quota_error(error_output: str, provider: str) -> bool:
    """
    Detect if error is due to quota/rate limit exhaustion.

    Checks for common quota error patterns from each provider.

    Args:
        error_output: Combined stderr and stdout from LLM call
        provider: LLM provider name (claude, gemini, codex)

    Returns:
        True if quota/rate limit error detected, False otherwise
    """
    error_lower = error_output.lower()

    # Common quota patterns across providers
    common_patterns = [
        "rate limit",
        "quota exceeded",
        "usage limit",
        "limit reached",
        "too many requests",
        "quota has been exceeded",
        "rate_limit_exceeded",
        "resource_exhausted"
    ]

    # Provider-specific patterns
    provider_patterns = {
        "codex": [
            "5-hour limit reached",
            "resets 3am",
            "/upgrade to max",
            "/extra-usage",
            "daily limit",
            "usage cap"
        ],
        "claude": [
            "rate limit exceeded",
            "usage limits",
            "maximum requests",
            "quota exceeded",
            "overloaded_error"
        ],
        "gemini": [
            "quota exceeded",
            "rate limit",
            "resource exhausted",
            "quota_exceeded",
            "rate_limit_error"
        ]
    }

    # Check common patterns
    for pattern in common_patterns:
        if pattern in error_lower:
            return True

    # Check provider-specific patterns
    if provider in provider_patterns:
        for pattern in provider_patterns[provider]:
            if pattern in error_lower:
                return True

    return False


def print_quota_warning(provider: str, error_output: str):
    """
    Print a clear, visible warning about quota exhaustion.

    Uses red text and clear formatting to make it highly visible.
    Provides actionable guidance on how to continue.

    Args:
        provider: LLM provider name (claude, gemini, codex)
        error_output: Combined stderr and stdout from LLM call
    """
    # ANSI color codes
    RED = '\033[0;31m'
    BOLD_RED = '\033[1;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

    # Extract relevant error message snippet
    error_snippet = ""
    if "5-hour limit reached" in error_output:
        # Extract the full Codex message
        lines = error_output.split('\n')
        for line in lines:
            if "limit reached" in line.lower() or "resets" in line.lower():
                error_snippet = line.strip()
                break

    # Build warning message
    provider_name = provider.capitalize()

    print("", file=sys.stderr)
    print(f"{BOLD_RED}{'=' * 80}{NC}", file=sys.stderr)
    print(f"{BOLD_RED}╔═══════════════════════════════════════════════════════════════════════════╗{NC}", file=sys.stderr)
    print(f"{BOLD_RED}║                                                                           ║{NC}", file=sys.stderr)
    print(f"{BOLD_RED}║  ⚠️  {provider_name.upper()} API QUOTA/RATE LIMIT REACHED  ⚠️                        ║{NC}", file=sys.stderr)
    print(f"{BOLD_RED}║                                                                           ║{NC}", file=sys.stderr)
    print(f"{BOLD_RED}╚═══════════════════════════════════════════════════════════════════════════╝{NC}", file=sys.stderr)
    print(f"{BOLD_RED}{'=' * 80}{NC}", file=sys.stderr)
    print("", file=sys.stderr)

    if error_snippet:
        print(f"{RED}Error message: {error_snippet}{NC}", file=sys.stderr)
        print("", file=sys.stderr)

    print(f"{YELLOW}What this means:{NC}", file=sys.stderr)
    print(f"  • The {provider_name} API has run out of quota or hit a rate limit", file=sys.stderr)
    print(f"  • All completed work has been preserved (resume will skip completed tasks)", file=sys.stderr)
    print("", file=sys.stderr)

    print(f"{YELLOW}Options to continue:{NC}", file=sys.stderr)

    if provider == "codex":
        print(f"  1. {YELLOW}Wait for quota reset{NC} (typically resets at 3am local time)", file=sys.stderr)
        print(f"     Then re-run the same command - resume will pick up where it left off", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  2. {YELLOW}Upgrade plan{NC}: Use '/upgrade to Max' or enable '/extra-usage'", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  3. {YELLOW}Switch provider{NC}: Edit overview.md to use 'claude' or 'gemini'", file=sys.stderr)
    elif provider == "claude":
        print(f"  1. {YELLOW}Wait for rate limit reset{NC} (typically resets hourly or daily)", file=sys.stderr)
        print(f"     Then re-run the same command - resume will pick up where it left off", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  2. {YELLOW}Upgrade plan{NC}: Consider Claude Pro or API tier upgrade", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  3. {YELLOW}Switch provider{NC}: Edit overview.md to use 'codex' or 'gemini'", file=sys.stderr)
    elif provider == "gemini":
        print(f"  1. {YELLOW}Wait for quota reset{NC} (typically resets daily)", file=sys.stderr)
        print(f"     Then re-run the same command - resume will pick up where it left off", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  2. {YELLOW}Upgrade plan{NC}: Consider Gemini Advanced or higher API tier", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  3. {YELLOW}Switch provider{NC}: Edit overview.md to use 'claude' or 'codex'", file=sys.stderr)
    else:
        print(f"  1. {YELLOW}Wait for quota reset{NC} and re-run", file=sys.stderr)
        print(f"  2. {YELLOW}Upgrade plan{NC} or switch to different provider", file=sys.stderr)

    print("", file=sys.stderr)
    print(f"{YELLOW}Resume capability:{NC}", file=sys.stderr)
    print(f"  • Your progress is saved - no work will be lost", file=sys.stderr)
    print(f"  • When you re-run, only failed tasks will be processed", file=sys.stderr)
    print(f"  • Example: If 196/224 tasks completed, only 28 will re-run", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"{BOLD_RED}{'=' * 80}{NC}", file=sys.stderr)
    print("", file=sys.stderr)
