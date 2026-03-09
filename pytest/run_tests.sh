#!/bin/bash
set -e

SUITE="${1:-all}"
shift 2>/dev/null || true
EXTRA_ARGS="$@"

echo ""
echo "============================================"
echo "  UnifAI Test Runner"
echo "============================================"
echo "  Suite       : $SUITE"
echo "  Extra args  : ${EXTRA_ARGS:-<none>}"
echo "============================================"
echo ""

HOME_DIR="$HOME"

case "$SUITE" in

  rag)
    echo ">>> Running RAG tests..."
    cd "$HOME_DIR/rag"
    exec pytest tests/ -v --tb=short --color=yes $EXTRA_ARGS
    ;;

  rag-unit)
    echo ">>> Running RAG unit tests..."
    cd "$HOME_DIR/rag"
    exec pytest tests/unit/ -v -s --tb=short --color=yes $EXTRA_ARGS
    ;;

  rag-e2e)
    echo ">>> Running RAG e2e tests..."
    cd "$HOME_DIR/rag"
    exec pytest tests/e2e/ -v -s --tb=short --color=yes $EXTRA_ARGS
    ;;

  multi-agent)
    echo ">>> Running Multi-Agent tests..."
    cd "$HOME_DIR/multi-agent"
    exec pytest tests/ -v --tb=short --color=yes $EXTRA_ARGS
    ;;

  multi-agent-e2e)
    echo ">>> Running Multi-Agent e2e tests..."
    cd "$HOME_DIR/multi-agent"
    exec pytest tests/e2e/ -v -s --tb=short --color=yes $EXTRA_ARGS
    ;;

  multi-agent-unit)
    echo ">>> Running Multi-Agent unit tests..."
    cd "$HOME_DIR/multi-agent"
    exec pytest tests/unit/ -v --tb=short --color=yes $EXTRA_ARGS
    ;;

  multi-agent-integration)
    echo ">>> Running Multi-Agent integration tests..."
    cd "$HOME_DIR/multi-agent"
    exec pytest tests/integration/ -v --tb=short --color=yes $EXTRA_ARGS
    ;;

  all)
    echo ">>> Running ALL tests..."
    echo ""

    echo "--- RAG tests ---"
    cd "$HOME_DIR/rag"
    pytest tests/ -v --tb=short --color=yes $EXTRA_ARGS || RAG_EXIT=$?
    echo ""

    echo "--- Multi-Agent tests ---"
    cd "$HOME_DIR/multi-agent"
    pytest tests/ -v --tb=short --color=yes $EXTRA_ARGS || MA_EXIT=$?
    echo ""

    echo "============================================"
    echo "  Results"
    echo "============================================"
    echo "  RAG          : ${RAG_EXIT:-0} (0=pass)"
    echo "  Multi-Agent  : ${MA_EXIT:-0} (0=pass)"
    echo "============================================"

    if [ "${RAG_EXIT:-0}" -ne 0 ] || [ "${MA_EXIT:-0}" -ne 0 ]; then
      exit 1
    fi
    ;;

  *)
    echo "ERROR: Unknown suite '$SUITE'"
    echo ""
    echo "Usage: $0 <suite> [pytest-args...]"
    echo ""
    echo "Available suites:"
    echo "  all                  - Run everything"
    echo "  rag                  - All RAG tests"
    echo "  rag-unit             - RAG unit tests only"
    echo "  rag-e2e              - RAG e2e tests only"
    echo "  multi-agent          - All multi-agent tests"
    echo "  multi-agent-e2e      - Multi-agent e2e tests only"
    echo "  multi-agent-unit     - Multi-agent unit tests only"
    echo "  multi-agent-integration - Multi-agent integration tests only"
    echo ""
    echo "Examples:"
    echo "  $0 rag-e2e --num-docs 10 --concurrent-uploads 5"
    echo "  $0 multi-agent -m unit"
    echo "  $0 all --junitxml=/tmp/results.xml"
    exit 1
    ;;
esac
