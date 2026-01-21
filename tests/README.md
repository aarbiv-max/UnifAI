# UnifAI Test Suite

Comprehensive tests for validating document processing and embedding pipeline in both local and remote modes.

---

## Quick Start

### Run All Local Tests (No Services Required)

```bash
# 1. Set test document path
export TEST_DOCUMENT_PATH=/path/to/your/test.pdf

# 2. Run all local tests
cd /path/to/UnifAI
pytest tests/ -v -s -k "local" -W ignore::DeprecationWarning
```

### Run All Remote Tests (Services Required)

```bash
# 1. Set environment variables
export TEST_DOCUMENT_PATH=/path/to/your/test.pdf
export DOCLING_SERVICE_URL=https://your-docling-service/
export EMBEDDING_SERVICE_URL=https://your-embedding-service/

# 2. Run all remote tests
pytest tests/ -v -s -k "remote" -W ignore::DeprecationWarning
```

### Run Everything

```bash
# All tests (local + remote)
export TEST_DOCUMENT_PATH=/path/to/your/test.pdf
export DOCLING_SERVICE_URL=https://your-docling-service/
export EMBEDDING_SERVICE_URL=https://your-embedding-service/

pytest tests/ -v -s -W ignore::DeprecationWarning
```

---

## Prerequisites

| Requirement | For Local Tests | For Remote Tests |
|-------------|-----------------|------------------|
| Python 3.10+ | ✓ Required | ✓ Required |
| TEST_DOCUMENT_PATH | ✓ Required (PDF file) | ✓ Required (PDF file) |
| Docling Service | Not needed | ✓ Required |
| Embedding Service | Not needed | ✓ Required |
| RabbitMQ | Not needed | Only for Celery tests |

### Install Dependencies

```bash
cd /path/to/UnifAI

# Install test requirements
pip install pytest numpy

# Install RAG requirements
pip install -r rag/requirements.txt

# Install global_utils
pip install -e global_utils/
```

---

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `TEST_DOCUMENT_PATH` | Yes | `/Users/me/test.pdf` | Path to test PDF file |
| `DOCLING_SERVICE_URL` | Remote only | `https://docling-service.example.com` | Docling service URL |
| `EMBEDDING_SERVICE_URL` | Remote only | `https://embedding-service.example.com` | Embedding service URL |
| `EMBEDDING_MODEL_NAME` | No | `all-MiniLM-L6-v2` | Model name (default) |
| `DOCLING_SERVICE_TIMEOUT` | No | `300` | Timeout in seconds |
| `EMBEDDING_SERVICE_TIMEOUT` | No | `60` | Timeout in seconds |

---

## Test Categories

| Category | Command | Services Required |
|----------|---------|-------------------|
| **Embedding Local** | `pytest tests/embedding/test_embedding_local.py -v -s` | None |
| **Embedding Remote** | `pytest tests/embedding/test_embedding_remote.py -v -s` | Embedding Service |
| **Docling Local** | `pytest tests/docling/test_docling_local.py -v -s` | None |
| **Docling Remote** | `pytest tests/docling/test_docling_remote.py -v -s` | Docling Service |
| **E2E Local** | `pytest tests/e2e/test_e2e_local.py -v -s` | None |
| **E2E Remote** | `pytest tests/e2e/test_e2e_remote.py -v -s` | Both Services |
| **Orchestration Local** | `pytest tests/e2e/test_e2e_orchestration_local.py -v -s` | None |
| **Orchestration Remote** | `pytest tests/e2e/test_e2e_orchestration_remote.py -v -s` | Both Services |
| **Celery Integration** | `pytest tests/e2e/test_e2e_celery_integration.py -v -s` | None (sync mode) |

---

## Test Report Format

Each test produces a detailed report (use `-s` flag to see output):

```
================================================================================
  TEST: Process Document
================================================================================
  Mode:        LOCAL
  Timestamp:   2026-01-21T14:47:40.123456
  Description: Validates document is processed and returns text + markdown content
  Status:      ✓ PASS
--------------------------------------------------------------------------------
  METRICS:
    • input_size_mb: 0.2345
    • processing_time_seconds: 2.1234
    • text_length_chars: 15234
    • text_length_words: 2456

  RESULTS:
    • input_file: Sample-pdf.pdf
    • output_keys: ['text', 'markdown', 'metadata']
    • text_preview: Lorem ipsum dolor sit amet...

  VALIDATIONS:
    ✓ result_not_none: expected=True, actual=True
    ✓ text_extracted: expected=True, actual=True
    ✓ markdown_extracted: expected=True, actual=True
================================================================================
```

---

## Directory Structure

```
tests/
├── README.md                           # This file
├── setup_env.sh                        # Environment setup script
├── conftest.py                         # Shared fixtures & TestReport
│
├── embedding/                          # Embedding unit tests
│   ├── test_embedding_local.py         # Local SentenceTransformer
│   └── test_embedding_remote.py        # Remote embedding service
│
├── docling/                            # Document connector tests
│   ├── test_docling_local.py           # Local docling library
│   └── test_docling_remote.py          # Remote docling service
│
└── e2e/                                # End-to-end tests
    ├── test_e2e_local.py               # Full pipeline local
    ├── test_e2e_remote.py              # Full pipeline remote
    ├── test_e2e_orchestration_local.py # DocumentPipelineHandler local
    ├── test_e2e_orchestration_remote.py# DocumentPipelineHandler remote
    └── test_e2e_celery_integration.py  # Celery task simulation
```

---

## Common Commands

### By Test Type

```bash
# Unit tests only
pytest tests/embedding/ tests/docling/ -v -s

# E2E tests only
pytest tests/e2e/ -v -s

# Specific test file
pytest tests/docling/test_docling_local.py -v -s

# Specific test
pytest tests/docling/test_docling_local.py::TestDoclingLocal::test_process_document -v -s
```

### By Mode

```bash
# All local tests
pytest tests/ -v -s -k "local"

# All remote tests
pytest tests/ -v -s -k "remote"

# Skip slow tests
pytest tests/ -v -s -x --timeout=60
```

### Useful Options

| Option | Description |
|--------|-------------|
| `-v` | Verbose output (show test names) |
| `-s` | Show print output (required for reports) |
| `-x` | Stop on first failure |
| `-k "pattern"` | Filter tests by name |
| `--tb=short` | Shorter tracebacks |
| `-W ignore::DeprecationWarning` | Suppress warnings |

---

## Troubleshooting

### Tests Skipped

```
SKIPPED: TEST_DOCUMENT_PATH not set or file does not exist
```

**Solution:**
```bash
export TEST_DOCUMENT_PATH=/path/to/existing/file.pdf
ls -la $TEST_DOCUMENT_PATH  # Verify file exists
```

### Connection Refused (Remote Tests)

```
requests.exceptions.ConnectionError: Connection refused
```

**Solution:**
```bash
# Verify services are running
curl $DOCLING_SERVICE_URL/health
curl $EMBEDDING_SERVICE_URL/health
```

### Import Errors

```
ModuleNotFoundError: No module named 'infrastructure'
```

**Solution:**
```bash
# Run from UnifAI root directory
cd /path/to/UnifAI
export PYTHONPATH="${PYTHONPATH}:$(pwd)/rag:$(pwd)/global_utils/src"
```

### Timeout Errors

```
ReadTimeout: Read timed out
```

**Solution:**
```bash
export DOCLING_SERVICE_TIMEOUT=600
export EMBEDDING_SERVICE_TIMEOUT=120
```

---

## What's Being Tested

### Architecture Validation

```
┌─────────────────────────────────────────────────────────────────────┐
│                     UNIFIED CLASSES                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DocumentConnector                    SentenceTransformerEmbedding  │
│  ├── LOCAL MODE                       ├── LOCAL MODE                │
│  │   └── Uses docling library         │   └── Uses SentenceTransformer│
│  │                                    │                              │
│  └── REMOTE MODE                      └── REMOTE MODE               │
│      └── Uses DoclingServiceClient        └── Uses EmbeddingServiceClient│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Test Goals

| Goal | Description |
|------|-------------|
| **Functional Equivalence** | Local and remote modes produce equivalent results |
| **Architecture Compliance** | Hexagonal pattern (ports & adapters) works correctly |
| **Regression Prevention** | Catch issues when modifying unified classes |
| **Performance Baseline** | Timing benchmarks for local vs remote |
| **Integration Validation** | Full pipeline works end-to-end |

### Acceptance Criteria

| Test Type | Metric | Threshold |
|-----------|--------|-----------|
| Embedding | Cosine similarity (local vs remote) | >= 0.95 |
| Document | Text length ratio | >= 0.95 |
| E2E | Pipeline completion | 100% |

---

## Quick Reference

```bash
# === MINIMAL LOCAL TEST ===
TEST_DOCUMENT_PATH=/path/to/test.pdf pytest tests/docling/test_docling_local.py -v -s -W ignore::DeprecationWarning

# === MINIMAL REMOTE TEST ===
TEST_DOCUMENT_PATH=/path/to/test.pdf \
DOCLING_SERVICE_URL=https://your-docling-service/ \
pytest tests/docling/test_docling_remote.py -v -s -W ignore::DeprecationWarning

# === ALL LOCAL TESTS ===
TEST_DOCUMENT_PATH=/path/to/test.pdf pytest tests/ -v -s -k "local" -W ignore::DeprecationWarning

# === ALL REMOTE TESTS ===
TEST_DOCUMENT_PATH=/path/to/test.pdf \
DOCLING_SERVICE_URL=https://your-docling-service/ \
EMBEDDING_SERVICE_URL=https://your-embedding-service/ \
pytest tests/ -v -s -k "remote" -W ignore::DeprecationWarning
```
