set shell := ["zsh", "-cu"]

# Justfile - Task automation for TEJL projects
# https://github.com/casey/just

# Default recipe - show help
default:
    @just --list

# =============================================================================
# TEMPLATE MANAGEMENT
# =============================================================================

# Validate project structure against template requirements
validate:
    @./.template/scripts/validate.sh .

# Sync updates from template repository
sync-downstream:
    @./.template/scripts/sync-downstream.sh .

# Check for contributions to send upstream
sync-upstream:
    @./.template/scripts/sync-upstream.sh .

# =============================================================================
# DEVELOPMENT
# =============================================================================

# Install dependencies (override per project)
install:
    @echo "Override this recipe in your project's Justfile"

# Build the project (override per project)
build:
    docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "{{justfile_directory()}}:/app" -w /app python:{{trim(read(".python-version"))}}-alpine python3 -B website/build.py

# Run development server (override per project)
dev:
    @echo "Override this recipe in your project's Justfile"

# Run tests (override per project)
test:
    docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "{{justfile_directory()}}:/app" -w /app python:{{trim(read(".python-version"))}}-alpine sh -c "python3 -B website/build.py && python3 -B website/check.py && python3 -B website/check_templates.py && python3 -B website/check_release.py"
    node website/check_clipboard.cjs
    node --check website/assets/app.js

# Run linter (override per project)
lint:
    @echo "Override this recipe in your project's Justfile"

# Format code (override per project)
fmt:
    @echo "Override this recipe in your project's Justfile"

# =============================================================================
# DOCUMENTATION
# =============================================================================

# Render Mermaid diagrams from docs/diagrams/*.mmd into docs/assets/*.svg
diagrams:
    #!/usr/bin/env bash
    set -euo pipefail

    if ! command -v mmdc >/dev/null 2>&1; then
        if ! command -v pnpm >/dev/null 2>&1; then
            echo "ERROR: Mermaid CLI is required. Install mmdc or pnpm."
            echo "Install option: pnpm add -g @mermaid-js/mermaid-cli"
            exit 1
        fi
        RENDERER="pnpm dlx --allow-build=puppeteer @mermaid-js/mermaid-cli"
    else
        RENDERER="mmdc"
    fi

    # Set PUPPETEER_EXECUTABLE_PATH explicitly when your local renderer needs it.

    mkdir -p docs/assets

    shopt -s nullglob
    sources=(docs/diagrams/*.mmd)
    if [ ${#sources[@]} -eq 0 ]; then
        echo "No Mermaid source files found in docs/diagrams/"
        exit 0
    fi

    for source in "${sources[@]}"; do
        name="$(basename "${source%.mmd}")"
        target="docs/assets/${name}.svg"
        echo "Rendering ${source} -> ${target}"
        ${RENDERER} -i "${source}" -o "${target}" -c docs/diagrams/mermaid-config.json --backgroundColor transparent
    done

# Show current project status
status:
    @echo "=== Project Status ==="
    @echo ""
    @echo "Version: $(cat VERSION 2>/dev/null || echo 'Not set')"
    @echo ""
    @echo "Recent Work Orders:"
    @cat PROJECT-INTERNAL/WORK-ORDERS/registry.json 2>/dev/null | head -20 || echo "No registry found"

# Show work order count
wo-count:
    @echo "Work Orders:"
    @ls -1 PROJECT-INTERNAL/WORK-ORDERS/WO-*.md 2>/dev/null | wc -l | xargs echo "  Standard:"
    @ls -1 PROJECT-INTERNAL/WORK-ORDERS/CORRECTIVE/CWO-*.md 2>/dev/null | wc -l | xargs echo "  Corrective:"

# =============================================================================
# UTILITIES
# =============================================================================

# Clean build artifacts (override per project)
clean:
    @echo "Override this recipe in your project's Justfile"

# Show all AGENTS.md files
agents:
    @echo "=== AGENTS.md Files ==="
    @find . -name "AGENTS.md" -type f | sort

# Explicit network import of the reviewed immutable catalog only
templates-sync:
    docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "{{justfile_directory()}}:/app" -w /app python:{{trim(read(".python-version"))}}-alpine sh -c "apk add --no-cache curl >/dev/null && python3 -B website/templates_feed.py"

# Offline build from an already synced, revalidated cache
build-with-templates:
    docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "{{justfile_directory()}}:/app" -w /app python:{{trim(read(".python-version"))}}-alpine python3 -B website/build.py --include-templates
