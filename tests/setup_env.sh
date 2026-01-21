#!/bin/bash
# =============================================================================
# UnifAI Test Environment Setup
# =============================================================================
#
# Usage:
#   source tests/setup_env.sh
#
# Then run tests:
#   pytest tests/ -v -s -W ignore::DeprecationWarning
#
# =============================================================================

# -----------------------------------------------------------------------------
# REQUIRED: Update this path to your test PDF
# -----------------------------------------------------------------------------
export TEST_DOCUMENT_PATH="${TEST_DOCUMENT_PATH:-/path/to/your/test.pdf}"

# -----------------------------------------------------------------------------
# OPTIONAL: Remote service URLs (only needed for remote tests)
# -----------------------------------------------------------------------------
# Uncomment and update these for remote tests:

# export DOCLING_SERVICE_URL="https://docling-service-tag-ai--pipeline.apps.stc-ai-e1-pp.imap.p1.openshiftapps.com"
# export EMBEDDING_SERVICE_URL="https://embedding-service-tag-ai--pipeline.apps.stc-ai-e1-pp.imap.p1.openshiftapps.com"

# -----------------------------------------------------------------------------
# OPTIONAL: Timeouts and model configuration
# -----------------------------------------------------------------------------
export EMBEDDING_MODEL_NAME="${EMBEDDING_MODEL_NAME:-all-MiniLM-L6-v2}"
export EMBEDDING_SERVICE_TIMEOUT="${EMBEDDING_SERVICE_TIMEOUT:-60}"
export DOCLING_SERVICE_TIMEOUT="${DOCLING_SERVICE_TIMEOUT:-300}"

# -----------------------------------------------------------------------------
# Display Configuration
# -----------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    TEST ENVIRONMENT CONFIGURED                    ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                   ║"
echo "║  TEST_DOCUMENT_PATH: $TEST_DOCUMENT_PATH"
if [ -f "$TEST_DOCUMENT_PATH" ]; then
echo "║  Document Status:    ✓ File exists                               ║"
else
echo "║  Document Status:    ✗ FILE NOT FOUND - Update TEST_DOCUMENT_PATH║"
fi
echo "║                                                                   ║"
if [ -n "$DOCLING_SERVICE_URL" ]; then
echo "║  DOCLING_SERVICE_URL: $DOCLING_SERVICE_URL"
else
echo "║  DOCLING_SERVICE_URL: (not set - remote tests will skip)         ║"
fi
if [ -n "$EMBEDDING_SERVICE_URL" ]; then
echo "║  EMBEDDING_SERVICE_URL: $EMBEDDING_SERVICE_URL"
else
echo "║  EMBEDDING_SERVICE_URL: (not set - remote tests will skip)       ║"
fi
echo "║                                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  QUICK COMMANDS:                                                  ║"
echo "║                                                                   ║"
echo "║  All local tests:                                                 ║"
echo "║    pytest tests/ -v -s -k 'local' -W ignore::DeprecationWarning  ║"
echo "║                                                                   ║"
echo "║  All remote tests:                                                ║"
echo "║    pytest tests/ -v -s -k 'remote' -W ignore::DeprecationWarning ║"
echo "║                                                                   ║"
echo "║  Docling local only:                                              ║"
echo "║    pytest tests/docling/test_docling_local.py -v -s              ║"
echo "║                                                                   ║"
echo "║  Embedding local only:                                            ║"
echo "║    pytest tests/embedding/test_embedding_local.py -v -s          ║"
echo "║                                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
