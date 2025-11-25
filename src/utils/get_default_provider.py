#!/usr/bin/env python3
"""
Helper script to get default provider from config.yaml
Used by bash scripts to load system configuration.
"""

from system_config import get_default_provider

if __name__ == "__main__":
    print(get_default_provider())
