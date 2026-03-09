# PR: Stress Testing Infrastructure for Document RAG System

**Branch:** `GENIE-1376/story/stress-testing-for-doc-rag-system-with-dynamic-configuration`
**Jira:** GENIE-1376

---

## Summary

This PR introduces a complete, containerised **pytest-based stress testing framework** for the UnifAI RAG document upload and embedding pipeline. It replaces the previous ad-hoc test scripts with a structured, production-grade test infrastructure that can be deployed to OpenShift via a dedicated Helm chart and produce browsable HTML/XML reports.

---

## What Has Been Done

| Area | Description |
|------|-------------|
| **Test framework** | Built a full pytest test suite under `rag/tests/` with base classes, fixtures, factories, and organised `unit/` + `e2e/` directories |
| **Stress test runner** | 730-line async stress test engine (`stress_test_doc_upload.py`) that uploads N documents concurrently, triggers the embedding pipeline, and monitors Celery tasks via MongoDB |
| **Unit tests** | 77 isolated unit tests covering document validators, domain models, pipeline service, pipeline executor, document pipeline handler, data source service, and retrieval service — all using mocked dependencies with zero infrastructure required |
| **Smoke tests** | Health-check tests that validate Docling, Embedding, and upload-readiness endpoints before running heavier tests |
| **Helm chart** | `helm/unifai-tests/` — deploys a test-runner pod, PVC for reports, ClusterIP service, and OpenShift Route for browsing results |
| **Docker image** | `tests/Dockerfile.pytest` — UBI9/Python 3.11 image with all RAG + multi-agent source, pytest plugins, and the test entrypoint |
| **Test runner script** | `tests/run_tests.sh` — entrypoint supporting multiple test suites (`rag`, `rag-unit`, `rag-e2e`, `multi-agent`, `all`, `debug`) with optional HTML/JUnit report generation and a built-in HTTP report server |
| **Archive** | Previous standalone test scripts moved to `tests/archive/` for reference |

---

## Test Inventory

### Total: **82 test functions** across 9 test files

---

#### Smoke Tests — `rag/tests/unit/test_service_health.py` (4 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 1 | `test_readiness_endpoint_responds` | `/health/service.readiness.get` returns HTTP 200 |
| 2 | `test_docling_service_healthy` | Docling service reports `status: healthy` |
| 3 | `test_embedding_service_healthy` | Embedding service reports `status: healthy` |
| 4 | `test_upload_enabled` | `upload_enabled` is `true` when both services are healthy |

#### E2E / Stress Tests — `rag/tests/e2e/test_doc_upload_stress.py` (1 test)

| # | Test | What it validates |
|---|------|-------------------|
| 5 | `test_full_upload_and_embed_flow` | Full upload → embed → Celery monitoring flow with configurable doc count and concurrency; asserts ≥95% success rate for both uploads and embeddings |

---

#### Unit Tests — Document Validators — `rag/tests/unit/test_document_validators.py` (17 tests)

These tests cover the **upload gatekeepers** — the validators that decide whether a file upload should be accepted or rejected *before* any processing happens. All validators return `(bool, Optional[ValidationIssue])`.

**ExtensionValidator** — checks if the uploaded file has a supported file type (e.g. `.pdf`, `.docx`):

- **`test_valid_extension_passes`** — A file named `report.pdf` should be accepted because `.pdf` is in the supported list. Confirms the basic happy path works.
- **`test_unsupported_extension_rejected`** — A file named `malware.exe` should be rejected because `.exe` is not supported. Confirms the validator actually blocks bad file types, and that the error message includes the rejected extension.
- **`test_no_extension_rejected`** — A filename like `readme` (no dot, no extension) should be rejected. Without an extension, we can't determine the file type.
- **`test_empty_filename_passes`** — When no filename is provided at all (empty string), the validator shouldn't crash — it passes and lets other validators handle it. This tests defensive behavior.
- **`test_case_insensitive`** — `REPORT.PDF` (uppercase) should be treated the same as `report.pdf`. Users shouldn't be rejected because their OS capitalizes file extensions.
- **`test_issue_contains_supported_types`** — When a file is rejected, the error message should tell the user *which* file types are actually supported, so they know what to upload instead.

**SizeValidator** — checks if a file exceeds the maximum allowed size (default 50 MB):

- **`test_file_under_limit_passes`** — A 1 KB file should pass. Basic happy path.
- **`test_file_over_limit_rejected`** — A file exceeding the limit should be rejected, and the error message should show the actual file size vs the max allowed (in MB).
- **`test_file_at_exact_limit_passes`** — A file that is *exactly* at the limit (e.g. 2048 bytes with a 2048 limit) should pass. This is a boundary test — "at the limit" is not "over the limit."
- **`test_nonexistent_file_passes`** — If the file path doesn't exist on disk, the validator shouldn't crash. It gracefully passes and lets other parts of the system handle the missing file.
- **`test_custom_max_size`** — The validator accepts a configurable max size. This confirms that passing a custom threshold (e.g. 500 bytes) actually works.
- **`test_os_error_passes_gracefully`** — If the OS throws an error when reading the file size (e.g. disk failure), the validator shouldn't crash the whole upload. It should **fail-open** (allow the upload) rather than block a potentially valid upload.

**DuplicateValidator** — checks if the *content* (MD5 hash) of the file already exists in the system:

- **`test_not_duplicate_passes`** — A new, unique file should be accepted.
- **`test_duplicate_rejected`** — If the checker says "this content already exists," the upload should be rejected, and the error message should include the filename.
- **`test_checker_exception_passes_gracefully`** — If the database is down and the duplicate checker throws an error, the validator shouldn't block the upload. It **fails-open** rather than preventing a potentially valid upload.

**NameDuplicateValidator** — checks if a file with the *same name* was already uploaded by the *same user*:

- **`test_no_duplicate_passes`** — A filename that doesn't exist yet for this user should be accepted.
- **`test_duplicate_name_rejected`** — If `existing.pdf` was already uploaded by Alice and is in `DONE` status, a second upload with the same name should be rejected. The error message should include both the filename and the status of the existing document.
- **`test_empty_source_name_passes`** — An empty filename defers to other validators rather than crashing.

**DocValidators factory** — assembles the correct list of validators depending on the upload flow:

- **`test_full_validation_returns_all_four`** — When `skip_validation=False` (external API call), all 4 validators run in order: extension → size → name duplicate → MD5 duplicate. This is the full validation pipeline for API uploads that didn't pre-validate.
- **`test_skip_validation_returns_only_duplicate`** — When `skip_validation=True` (UI flow where files were already pre-validated via `/docs/validate`), only the MD5 duplicate check runs. This is because content can only be checked after the file is uploaded.

---

#### Unit Tests — Domain Models — `rag/tests/unit/test_domain_models.py` (9 tests)

These tests verify the **data structures** — making sure objects serialize and deserialize correctly and have sensible defaults. If these break, data gets corrupted silently when reading from or writing to MongoDB.

**PipelineStats:**

- **`test_from_dict_with_all_fields`** — When you create a `PipelineStats` from a dictionary with all fields populated, every field should be correctly assigned. Confirms the constructor mapping works.
- **`test_from_dict_with_missing_fields_defaults_to_zero`** — If the dictionary only has `documents_retrieved`, all other fields (`chunks_generated`, `api_calls`, etc.) should default to `0` rather than crashing. This is important because older MongoDB records may not have all fields.
- **`test_to_dict_round_trip`** — Create a `PipelineStats` object, convert it to a dict, then convert it back. The result should be identical to the original. This catches serialization bugs that would silently corrupt data.

**PipelineRecord:**

- **`test_from_dict_valid_status`** — The string `"DONE"` from MongoDB should correctly map to the `PipelineStatus.DONE` enum value.
- **`test_from_dict_invalid_status_defaults_to_pending`** — If the database contains a garbage status like `"BOGUS"`, the code should fall back to `PENDING` rather than crashing. This is defensive parsing for data integrity.
- **`test_to_dict_serializes_status_as_string`** — When converting to a dict (for JSON/MongoDB), the status should be the string `"COLLECTING"`, not the Python enum object. Otherwise JSON serialization would fail.

**DataSource:**

- **`test_from_dict_round_trip`** — Same round-trip concept: create a `DataSource`, serialize to dict, deserialize back, verify all fields match.
- **`test_defaults`** — A `DataSource` created without `tags`, `type_data`, or `last_sync_at` should get sensible defaults: empty list, empty dict, and `None` respectively. Prevents null pointer errors downstream.

**PipelineStartResult:**

- **`test_to_dict_with_dispatched_tasks`** — When tasks were dispatched (sources registered successfully), the result's `to_dict()` should show `status: "pipeline_workflow_started"` and the correct task count. This is the response body the API returns.
- **`test_to_dict_with_no_sources`** — When no sources were registered, the result should show `status: "no_registered_sources"` with a message explaining nothing was dispatched. This tells the caller why nothing happened.

---

#### Unit Tests — Pipeline Service — `rag/tests/unit/test_pipeline_service.py` (9 tests)

These tests cover `PipelineService`, which manages pipeline records (CRUD + status tracking). The `PipelineRepository` (database layer) is mocked.

- **`test_register_creates_new_record`** — When registering a pipeline that doesn't exist yet, a new record should be created with `PENDING` status and saved to the repository.
- **`test_register_existing_updates_timestamp`** — When registering a pipeline that already exists, it should NOT create a duplicate. Instead, it refreshes the `last_updated` timestamp. This makes registration idempotent — safe to call multiple times.
- **`test_update_status_success`** — Updating the status of an existing pipeline should change the status field and persist to the repository.
- **`test_update_status_calculates_processing_time_on_done`** — When a pipeline reaches `DONE`, the service automatically calculates how long it took (difference between `created_at` and now) and stores it in `stats.processing_time`. This only happens for `DONE`, not for intermediate statuses.
- **`test_update_status_no_processing_time_on_other_statuses`** — When updating to `COLLECTING`, `FAILED`, etc., the `processing_time` should remain `0.0`. We only calculate it when the pipeline finishes successfully.
- **`test_update_status_from_string`** — The service accepts both the enum `PipelineStatus.PROCESSING` and the raw string `"PROCESSING"`. This test confirms the string-to-enum conversion works, which is important because status values may come from HTTP requests as strings.
- **`test_update_status_nonexistent_returns_false`** — If you try to update a pipeline that doesn't exist, the service should return `False` and not attempt to save anything. No crash, no silent failure.
- **`test_get_delegates_to_repo`** — The `get()` method is a thin passthrough to the repository. This test confirms it calls `find_by_id` with the correct ID.
- **`test_delete_delegates_to_repo`** — Same for `delete()` — it passes through to the repository and returns the count of deleted records.

---

#### Unit Tests — Pipeline Executor — `rag/tests/unit/test_pipeline_executor.py` (12 tests)

These tests cover `PipelineExecutor`, the **orchestrator** that runs the full pipeline (Collect → Process → Chunk & Embed → Store) and handles failures. This is the most complex and critical component — the tests verify status transitions, error recording, and cleanup guarantees.

**Happy path:**

- **`test_happy_path_status_transitions`** — On a successful run, the executor should update the pipeline status in this exact order: `COLLECTING` → `PROCESSING` → `CHUNKING_AND_EMBEDDING` → `STORING` → `DONE`. This verifies the orchestration sequence is correct.
- **`test_happy_path_stores_embeddings`** — After chunking and embedding, the results should be stored in the vector repository. This confirms the final step actually persists data to Qdrant.
- **`test_happy_path_upserts_source_with_summary`** — After a successful pipeline, the executor should update the data source record with a summary (page count, text, file size). This is how the UI knows the pipeline finished and can display document details.

**Failure at each pipeline step:**

- **`test_failure_at_collect_records_error`** — If `collect()` throws an error, the executor should: record the error with `failed_at: COLLECTING`, and set the pipeline status to `FAILED`. This ensures failures at the first step are properly tracked.
- **`test_failure_at_process_records_error`** — Same pattern but for the process step. The `failed_at` field should say `PROCESSING`, so operators know exactly where it broke.
- **`test_failure_at_chunk_and_embed_records_error`** — Same for chunk_and_embed. `failed_at: CHUNKING_AND_EMBEDDING`.
- **`test_failure_at_store_records_error`** — Same for the vector storage step. `failed_at: STORING`. Important because this is the step that talks to Qdrant, which may be down.
- **`test_failure_upserts_source_with_error_info`** — When a pipeline fails, the executor should still update the data source record, but with error information (`last_error` message and `failed_at` step) instead of a success summary. This is how the UI shows what went wrong to the user.

**Cleanup guarantees:**

- **`test_cleanup_always_called_on_success`** — After a successful pipeline, the executor should call `handler.cleanup()` (to delete temp files from disk) and `finish_log_monitoring()` (to remove the logging handler). This is the "finally" block.
- **`test_cleanup_always_called_on_failure`** — Even when the pipeline crashes, cleanup must still happen. Without this guarantee, temp files would leak on disk and logging handlers would accumulate in memory.
- **`test_exception_re_raised`** — After recording the error and cleaning up, the executor should re-raise the original exception so the Celery worker knows the task failed and can mark it accordingly.

**Monitoring:**

- **`test_monitoring_started_with_correct_pipeline_id`** — The log monitoring should be started with a pipeline ID in the format `"document_src_1"` (lowercase source_type + underscore + source_id). This ID is used to correlate log entries with the specific pipeline run.

---

#### Unit Tests — Document Pipeline Handler — `rag/tests/unit/test_document_pipeline_handler.py` (12 tests)

These tests cover `DocumentPipelineHandler`, which implements the document-specific logic for each pipeline step. All four dependencies (connector, processor, chunker, embedder) are mocked.

- **`test_source_type_is_document`** — The handler should identify itself as `"DOCUMENT"`. This string is used to route to the correct vector collection (`document_data`) and determine the pipeline ID format.
- **`test_collect_calls_connector`** — The collect step should call the document connector with the `doc_path` and `upload_by` extracted from the pipeline context metadata. If these arguments are wrong, the connector would process the wrong file or attribute it to the wrong user.
- **`test_collect_caches_result`** — After collecting, the handler should cache the raw document internally. This cache is later used by `get_summary()` to return document info without reprocessing.
- **`test_process_calls_processor_with_correct_flags`** — The process step should call the document processor with specific flags: `clean_markdown=False`, `clean_text=False`, `remove_references=False`, `preserve_original=True`. If these flags change accidentally, document processing behavior changes and could corrupt content.
- **`test_chunk_and_embed_enriches_metadata`** — Each chunk produced should have `source_id` and `source_type: "DOCUMENT"` added to its metadata. This is how vector search later filters results by specific documents or source type.
- **`test_chunk_and_embed_converts_numpy_embedding`** — Embeddings come back from the embedding service as numpy arrays, but need to be stored as plain Python lists (for JSON serialization and Qdrant storage). This test confirms the `.tolist()` conversion happens.
- **`test_chunk_and_embed_handles_list_embedding`** — If the embedding is already a plain list (not numpy), the handler should work without error. No double-conversion or crash.
- **`test_chunk_and_embed_returns_vector_chunks`** — The output should be a list of `VectorChunk` domain objects, not raw dictionaries. This confirms the data is properly wrapped in the domain model.
- **`test_get_summary_with_cached_document`** — When a document was collected (and cached), the summary should return its `page_count`, `full_text`, and `file_size`. This summary is stored in the data source record for the UI.
- **`test_get_summary_without_cached_document`** — When no document was collected (edge case — e.g. handler just created), the summary should return safe defaults: `page_count: 0`, `full_text: ""`, `file_size: 0`. No crash.
- **`test_cleanup_with_doc_path`** — After pipeline execution, the uploaded temp file on disk should be deleted via `cleanup_file()`. Without this, temp files would accumulate on the server.
- **`test_cleanup_without_doc_path`** — If the context has no `doc_path` (edge case), cleanup should return `False` without crashing.

---

#### Unit Tests — Data Source Service — `rag/tests/unit/test_data_source_service.py` (11 tests)

These tests cover `DataSourceService`, which manages the lifecycle of data sources — CRUD operations, cascade delete with consistency guarantees, upsert after pipeline, and enrichment with pipeline stats. All repositories are mocked.

**Delete (cascade with consistency):**

- **`test_delete_source_not_found`** — Trying to delete a source that doesn't exist should return `DeleteResult(success=False)` with a "not found" message. No crash.
- **`test_delete_happy_path`** — A successful delete should cascade in order: first delete vectors from Qdrant, then delete the pipeline record from MongoDB, then delete the source record. The result should report all three deletion counts.
- **`test_delete_vector_failure_aborts`** — If Qdrant is down and vector deletion fails, the whole delete should abort. We don't want to delete the MongoDB records while orphaning vectors in Qdrant — that would leave the system in an inconsistent state.
- **`test_delete_mongo_failure_partial`** — If vectors were deleted successfully but then MongoDB fails, the result should report a partial deletion with the vector count. The caller can see exactly what was cleaned up and what wasn't.
- **`test_delete_uses_correct_collection_name`** — For a `DOCUMENT` source, the vector repo factory should be called with `"document_data"` (lowercase type + `_data` suffix). A wrong collection name would mean deleting from the wrong Qdrant collection — data loss.

**Upsert after pipeline:**

- **`test_upsert_creates_new_source`** — When no source exists for the given pipeline_id, a new `DataSource` should be created and saved with the provided summary as `type_data`.
- **`test_upsert_updates_existing_source`** — When a source already exists, it should update `last_sync_at` to now and **merge** the new summary into existing `type_data` without overwriting existing fields. This preserves previous metadata while adding new information.

**Enrichment (for UI display):**

- **`test_enrich_empty_list`** — Enriching an empty list of sources should return an empty list. No crashes on empty input.
- **`test_enrich_with_pipeline_stats`** — When pipeline stats exist for a source, the enriched output should include `status: "DONE"` and the stats (like `chunks_generated: 10`). This is what the UI table displays.
- **`test_enrich_without_pipeline_stats`** — When no pipeline stats exist for a source (e.g. pipeline hasn't run yet), it should get `status: None` and `pipeline_stats: None` instead of crashing.

**Update:**

- **`test_update_existing_source`** — Updating valid attributes (like `source_name`) on an existing source should work and return `True`.
- **`test_update_nonexistent_source`** — Updating a source that doesn't exist should return `False` and not attempt to save.

---

#### Unit Tests — Retrieval Service — `rag/tests/unit/test_retrieval_service.py` (7 tests)

These tests cover `RetrievalService`, the search orchestrator that resolves filters, generates query embeddings, and executes vector search. All dependencies (embedder, vector repo, filter resolver) are mocked.

- **`test_search_no_filters`** — When no `doc_ids` or `tags` are provided, the search should run against *all* documents (no `metadata.source_id` filter applied). The query embedding should still be generated and vector search should execute normally.
- **`test_search_early_exit_empty_filter`** — When the filter resolver returns an empty set (meaning: filters were applied but nothing matched — e.g. the requested doc_ids don't exist), the service should return `[]` immediately *without* generating an embedding or querying the vector store. This is a performance optimization that avoids unnecessary work.
- **`test_search_with_doc_ids`** — When `doc_ids` are provided and the resolver finds matching source_ids, those should be passed as a `metadata.source_id` filter to the vector search. This scopes results to only the requested documents.
- **`test_search_private_scope`** — When `scope="private"`, the search should add a `metadata.upload_by` filter with the user's name. This ensures users only see their own documents in private mode.
- **`test_search_public_scope`** — When `scope="public"`, no `upload_by` filter should be added. Everyone sees the same public results.
- **`test_search_result_mapping`** — The raw `SearchResult` objects from the vector repository should be converted to plain dictionaries with `id`, `score`, `content`, and `metadata` keys. This is the format the REST API returns to clients.
- **`test_search_with_query_delegates`** — The convenience method `search_with_query(SearchQuery(...))` should unpack the query object's fields and call the main `search()` method with them. This confirms the two entry points produce identical behavior.

---

## Test Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Test Execution Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Container starts → run_tests.sh                             │
│     ├── Activates Python venv                                   │
│     ├── Optionally starts HTTP report server in background      │
│     └── Invokes pytest with selected suite                      │
│                                                                 │
│  2. Pytest collects tests                                       │
│     ├── conftest.py registers CLI options & markers             │
│     ├── Auto-adds markers based on directory (unit/e2e)         │
│     └── Session-scoped fixtures initialised once:               │
│         ├── rag_config (API URLs, MongoDB, load params)         │
│         ├── celery_monitor (MongoDB connection)                 │
│         └── document_factory + batch_pdf_documents              │
│                                                                 │
│  3. Unit tests run first (smoke / health)                       │
│     └── GET /health/service.readiness.get                       │
│         ├── Assert HTTP 200                                     │
│         ├── Assert Docling healthy                              │
│         ├── Assert Embedding healthy                            │
│         └── Assert upload_enabled = true                        │
│                                                                 │
│  4. E2E stress test runs                                        │
│     ├── PHASE 1: Upload                                         │
│     │   ├── Generate N unique 2-page PDFs (ReportLab)           │
│     │   ├── Upload concurrently in batches of M (aiohttp)       │
│     │   ├── Retry failed uploads with exponential backoff       │
│     │   └── Record UploadStats (success/fail/timing)            │
│     │                                                           │
│     ├── Trigger embedding pipeline (PUT /pipelines/embed)       │
│     │                                                           │
│     ├── PHASE 2: Monitor Celery tasks                           │
│     │   ├── Poll MongoDB celery_taskmeta collection             │
│     │   ├── Filter tasks by pipeline_id prefix "document_"      │
│     │   ├── Track SUCCESS / FAILURE / PENDING states            │
│     │   ├── Log progress every 30 seconds                       │
│     │   └── Wait until all tasks complete or timeout (30 min)   │
│     │                                                           │
│     └── PHASE 3: Assertions                                     │
│         ├── Upload success rate ≥ 95%                           │
│         ├── Embedding success rate ≥ 95%                        │
│         └── Print final report with timing statistics           │
│                                                                 │
│  5. Reports generated                                           │
│     ├── HTML report (pytest-html)                               │
│     ├── JUnit XML (pytest --junitxml)                           │
│     └── Served via HTTP on port 8080 (if enabled)               │
│                                                                 │
│  6. Container stays alive (tail -f /dev/null)                   │
│     └── Reports remain accessible via Route/port-forward        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
rag/tests/
├── conftest.py                          # Global config, CLI options, marker registration
├── base/
│   └── base_e2e_test.py                 # BaseE2ETest with assertion helpers
├── fixtures/
│   ├── common/
│   │   └── api_fixtures.py              # RagTestConfig, celery_monitor fixtures
│   └── document/
│       └── document_fixtures.py         # document_factory, sample/batch PDF fixtures
├── factories/
│   └── document_factory.py              # DocumentFactory — PDF generation via ReportLab
├── unit/
│   ├── test_service_health.py           # 4 smoke/health tests
│   ├── test_document_validators.py      # 17 document validator unit tests
│   ├── test_domain_models.py            # 9 domain model serialization tests
│   ├── test_pipeline_service.py         # 9 pipeline CRUD/status tests
│   ├── test_pipeline_executor.py        # 12 pipeline orchestration tests
│   ├── test_document_pipeline_handler.py # 12 document handler tests
│   ├── test_data_source_service.py      # 11 data source service tests
│   └── test_retrieval_service.py        # 7 retrieval/search tests
├── e2e/
│   └── test_doc_upload_stress.py        # 1 full-flow stress test
└── docs/
    └── stress_test_doc_upload.py        # StressTestRunner engine (730 lines)
```

---

## Deployment Guide

### Prerequisites

- Access to an OpenShift cluster with the UnifAI RAG stack deployed
- `helm` CLI (v3+)
- `oc` or `kubectl` CLI
- The test image pushed to your registry (or use the default)

### 1. Build and Push the Test Image

```bash
# From repo root
docker build -f tests/Dockerfile.pytest -t <registry>/unifai-tests:<tag> .
docker push <registry>/unifai-tests:<tag>
```

### 2. Install the Helm Chart

```bash
# Basic install (RAG tests with defaults)
helm install unifai-tests ./helm/unifai-tests

# With custom values
helm install unifai-tests ./helm/unifai-tests \
  --set image.repository=<registry>/unifai-tests \
  --set image.tag=<tag> \
  --set testSuite=rag \
  --set env.API_BASE_URL=http://unifai-rag-server:13456/api \
  --set env.NUM_DOCUMENTS=50 \
  --set env.CONCURRENT_UPLOADS=5
```

### 3. Available Test Suites

| Suite | Command | Scope |
|-------|---------|-------|
| `rag` | `--set testSuite=rag` | All RAG tests (unit + e2e) |
| `rag-unit` | `--set testSuite=rag-unit` | RAG unit/smoke tests only |
| `rag-e2e` | `--set testSuite=rag-e2e` | RAG e2e stress tests only |
| `multi-agent` | `--set testSuite=multi-agent` | All multi-agent tests |
| `all` | `--set testSuite=all` | Both RAG and multi-agent |
| `debug` | `--set testSuite=debug` | Print environment info and sleep (troubleshooting) |

### 4. Key Configuration Values

| Value | Default | Description |
|-------|---------|-------------|
| `image.repository` | `images.paas.redhat.com/unifai/unifai-tests` | Test image registry |
| `image.tag` | `latest` | Image tag |
| `testSuite` | `rag` | Test suite to run |
| `extraArgs` | `""` | Additional pytest arguments (e.g. `-k test_readiness`) |
| `env.API_BASE_URL` | `http://unifai-rag-server:13456/api` | RAG API base URL |
| `env.MONGODB_HOST` | `mongodb` | MongoDB host for Celery monitoring |
| `env.MONGODB_PORT` | `27017` | MongoDB port |
| `env.MONGODB_DB` | `celery` | Celery results database |
| `env.NUM_DOCUMENTS` | `10` | Number of documents for stress test |
| `env.CONCURRENT_UPLOADS` | `10` | Parallel upload count |
| `env.UPLOAD_TIMEOUT` | `300` | Per-upload timeout (seconds) |
| `env.UPLOAD_MAX_RETRIES` | `3` | Retry count per upload |
| `env.LOG_LEVEL` | `INFO` | Pytest log level |
| `reports.enabled` | `true` | Enable PVC + Service + Route for reports |
| `reports.storage.size` | `1Gi` | Report PVC size |
| `reports.storage.className` | `aws-efs-tier-c1` | Storage class |
| `reports.route.enabled` | `true` | Create OpenShift Route |
| `resources.limits.cpu` | `2` | CPU limit |
| `resources.limits.memory` | `4Gi` | Memory limit |
| `resources.requests.cpu` | `1` | CPU request |
| `resources.requests.memory` | `2Gi` | Memory request |

### 5. Monitor Test Execution

```bash
# Watch live test output
oc logs deploy/unifai-tests-unifai-tests -f

# Check pod status
oc get pods -l app.kubernetes.io/name=unifai-tests
```

### 6. Access Test Reports

```bash
# Via OpenShift Route (if reports.route.enabled=true)
oc get route unifai-tests-unifai-tests-reports -o jsonpath='{.spec.host}'
# Open https://<host> in your browser

# Via port-forward (if route is disabled)
oc port-forward deploy/unifai-tests-unifai-tests 8080:8080
# Open http://localhost:8080
```

### 7. Re-run Tests

```bash
# Delete the pod to trigger a re-run (deployment recreates it)
oc delete pod -l app.kubernetes.io/name=unifai-tests

# Or upgrade with different parameters
helm upgrade unifai-tests ./helm/unifai-tests \
  --set env.NUM_DOCUMENTS=200 \
  --set testSuite=rag-e2e
```

### 8. Uninstall

```bash
helm uninstall unifai-tests

# Note: The PVC is retained (resource-policy: keep).
# To fully clean up:
oc delete pvc unifai-tests-unifai-tests-reports
```

---

## Files Changed

| Path | Description |
|------|-------------|
| `rag/pytest.ini` | Pytest configuration (markers, timeouts, discovery) |
| `rag/tests/conftest.py` | Global fixtures, CLI options, auto-marking |
| `rag/tests/base/base_e2e_test.py` | Base class with assertion helpers |
| `rag/tests/fixtures/common/api_fixtures.py` | `RagTestConfig` + `celery_monitor` fixtures |
| `rag/tests/fixtures/document/document_fixtures.py` | PDF document fixtures |
| `rag/tests/factories/document_factory.py` | `DocumentFactory` for generating test PDFs |
| `rag/tests/unit/test_service_health.py` | 4 service health smoke tests |
| `rag/tests/unit/test_document_validators.py` | 17 document validator unit tests (extension, size, duplicate, name duplicate, factory) |
| `rag/tests/unit/test_domain_models.py` | 9 domain model unit tests (PipelineStats, PipelineRecord, DataSource, PipelineStartResult) |
| `rag/tests/unit/test_pipeline_service.py` | 9 pipeline service unit tests (register, update_status, get, delete) |
| `rag/tests/unit/test_pipeline_executor.py` | 12 pipeline executor unit tests (status transitions, failure handling, cleanup guarantees) |
| `rag/tests/unit/test_document_pipeline_handler.py` | 12 document handler unit tests (collect, process, chunk_and_embed, get_summary, cleanup) |
| `rag/tests/unit/test_data_source_service.py` | 11 data source service unit tests (delete cascade, upsert, enrich, update) |
| `rag/tests/unit/test_retrieval_service.py` | 7 retrieval service unit tests (filter logic, scope, result mapping) |
| `rag/tests/e2e/test_doc_upload_stress.py` | E2E stress test (upload + embed + verify) |
| `rag/tests/docs/stress_test_doc_upload.py` | `StressTestRunner` engine (730 lines) |
| `tests/Dockerfile.pytest` | Container image definition |
| `tests/run_tests.sh` | Multi-suite test entrypoint script |
| `tests/README.md` | Test infrastructure documentation |
| `helm/unifai-tests/*` | Helm chart (deployment, PVC, service, route, values) |
| `tests/archive/*` | Archived previous test scripts |

---

## Expected Results and How to Evaluate

### Quick Summary

When running the full `rag` test suite, you should see:

```
87 passed
```

All **87 tests** should pass. Zero failures, zero errors. If any test fails, it indicates a real issue — these tests do not have flaky behavior.

### Expected Output Per Test File

| Test File | Tests | Expected Result | What a Failure Means |
|-----------|-------|-----------------|----------------------|
| `test_service_health.py` | 4 | All PASSED | The RAG server, Docling, or Embedding service is down or unreachable. Check pod health and network connectivity. |
| `test_doc_upload_stress.py` | 1 | PASSED with upload success rate >= 95% and embedding success rate >= 95% | The upload endpoint or embedding pipeline is failing under load. Check RAG server logs and Celery worker logs. |
| `test_document_validators.py` | 17 | All PASSED | A validator's accept/reject logic has changed. Check if the change was intentional — validators control what files users can upload. |
| `test_domain_models.py` | 9 | All PASSED | A domain model's serialization or defaults have changed. This can silently corrupt data in MongoDB. Check `from_dict()` / `to_dict()` methods. |
| `test_pipeline_service.py` | 9 | All PASSED | Pipeline record management (status tracking, registration, processing time) is broken. Check `PipelineService` and `PipelineRepository`. |
| `test_pipeline_executor.py` | 12 | All PASSED | The pipeline orchestration flow is broken — status transitions, error handling, or cleanup guarantees may have regressed. This is critical: failures here can cause leaked temp files, missing error records, or silent pipeline failures. |
| `test_document_pipeline_handler.py` | 12 | All PASSED | Document-specific pipeline logic has changed — connector calls, processor flags, metadata enrichment, or cleanup behavior. Check `DocumentPipelineHandler`. |
| `test_data_source_service.py` | 11 | All PASSED | Data source CRUD or cascade delete logic is broken. Failures in delete tests may indicate data consistency issues (e.g. orphaned vectors in Qdrant). |
| `test_retrieval_service.py` | 7 | All PASSED | Search/retrieval logic has changed — filter resolution, scope filtering, or result mapping. Users may get wrong search results or see other users' private documents. |

### How to Read the Logs

**Unit tests (77 tests)** — These run with mocked dependencies and require no infrastructure. They execute instantly. In the logs, you'll see:

- `PASSED` next to each test name — this is the expected result.
- Occasional `WARNING` log lines like `"Duplicate check failed for report.pdf, allowing upload: db down"` — these are **expected**. They come from the source code's fail-open error handling and confirm the test is exercising the real code path.
- `INFO` log lines like `"Collecting document: /tmp/report.pdf"` or `"Filter resolved to empty set - returning no results"` — also **expected**. These come from the source code's logger and confirm the mocks are wired correctly.

**Smoke tests (4 tests)** — These make real HTTP calls to the running RAG server. They verify:

- The readiness endpoint responds with HTTP 200
- Docling reports `status: healthy`
- Embedding reports `status: healthy`
- `upload_enabled` is `true`

If any smoke test fails, do **not** proceed with the E2E stress test — the system is not ready.

**E2E stress test (1 test)** — This runs the full upload-and-embed flow. In the logs, look for:

- **PHASE 1: DOCUMENT UPLOAD** — All documents should upload successfully. Look for `"Progress: N/N successful, 0 failed"`.
- **Embedding pipeline triggered** — Should show `"pipeline_workflow_started"` with the correct number of tasks.
- **PHASE 2: MONITORING CELERY TASKS** — All tasks should complete with `SUCCESS` status. Look for `"All Celery tasks completed!"`.
- **STRESS TEST FINAL REPORT** — Upload success rate and embedding success rate should both be >= 95%. Look for `"STRESS TEST PASSED"`.

### Running Specific Test Subsets

```bash
# All RAG tests (unit + smoke + e2e)
helm install unifai-tests ./helm/unifai-tests --set testSuite=rag

# Only unit tests (no infrastructure needed beyond the RAG server image)
helm install unifai-tests ./helm/unifai-tests --set testSuite=rag-unit

# Only E2E stress tests
helm install unifai-tests ./helm/unifai-tests --set testSuite=rag-e2e

# Run a specific test file or test name
helm install unifai-tests ./helm/unifai-tests \
  --set testSuite=rag \
  --set extraArgs="-k test_pipeline_executor"
```
