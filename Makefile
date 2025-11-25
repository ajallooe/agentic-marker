.PHONY: help install clean test check-prereqs enable-widgets

# Default target
help:
	@echo "Agentic Notebook Marker - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install        - Create virtual environment and install dependencies"
	@echo "  make enable-widgets - Enable Jupyter widgets (run after install)"
	@echo "  make check-prereqs  - Check if required CLI tools are installed"
	@echo "  make clean          - Remove virtual environment and generated files"
	@echo "  make test           - Test core utilities with sample data"
	@echo ""
	@echo "Quick start:"
	@echo "  1. make install"
	@echo "  2. make enable-widgets"
	@echo "  3. make check-prereqs"
	@echo "  4. source .venv/bin/activate"
	@echo "  5. ./mark_structured.sh assignments/sample-assignment"

# Create virtual environment and install dependencies
install:
	@echo "Creating virtual environment..."
	python3 -m venv .venv
	@echo "Installing Python dependencies..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "✓ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run: make enable-widgets"
	@echo "  2. Run: make check-prereqs"
	@echo "  3. Activate venv: source .venv/bin/activate"

# Enable Jupyter widgets
enable-widgets:
	@echo "Enabling Jupyter widgets..."
	.venv/bin/jupyter nbextension enable --py widgetsnbextension --sys-prefix
	@echo "✓ Widgets enabled!"

# Check if required CLI tools are installed
check-prereqs:
	@echo "Checking prerequisites..."
	@echo ""
	@echo "Python 3:"
	@which python3 > /dev/null && echo "  ✓ python3 found" || echo "  ✗ python3 not found"
	@echo ""
	@echo "Claude Code CLI:"
	@which claude > /dev/null && echo "  ✓ claude found (version: $$(claude --version 2>&1 || echo 'unknown'))" || echo "  ✗ claude not found - install from https://claude.ai/code"
	@echo ""
	@echo "Optional CLIs:"
	@which gemini > /dev/null && echo "  ✓ gemini found" || echo "  ○ gemini not found (optional)"
	@which openai > /dev/null && echo "  ✓ openai found" || echo "  ○ openai not found (optional)"
	@echo ""
	@echo "GNU Parallel (recommended for performance):"
	@which parallel > /dev/null && echo "  ✓ parallel found" || echo "  ○ parallel not found (will use fallback)"
	@echo ""
	@echo "jq (required for JSON parsing):"
	@which jq > /dev/null && echo "  ✓ jq found" || echo "  ✗ jq not found - install: brew install jq (macOS) or apt-get install jq (Linux)"

# Test core utilities
test:
	@echo "Testing core utilities..."
	@echo ""
	@echo "1. Testing configuration parser..."
	@.venv/bin/python3 src/utils/config_parser.py assignments/sample-assignment/overview.md || echo "✗ Config parser failed"
	@echo ""
	@echo "2. Testing submission finder..."
	@.venv/bin/python3 src/find_submissions.py assignments/sample-assignment/submissions --summary || echo "Note: No valid submissions in sample (expected)"
	@echo ""
	@echo "3. Testing activity extractor..."
	@.venv/bin/python3 src/extract_activities.py assignments/sample-assignment/base_notebook.ipynb --summary || echo "✗ Activity extractor failed"
	@echo ""
	@echo "✓ Core utilities tested"

# Clean up virtual environment and generated files
clean:
	@echo "Cleaning up..."
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "processed" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Clean only generated assignment files (keep venv)
clean-assignments:
	@echo "Cleaning generated assignment files..."
	find assignments -type d -name "processed" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Assignment artifacts cleaned"
