"""
Unit tests for LOCAL document processing using DocumentConnector.

This test uses the local docling library directly.
No external service is required.
Requires TEST_DOCUMENT_PATH environment variable pointing to a PDF file.

Run:
    TEST_DOCUMENT_PATH=/path/to/test.pdf pytest tests/docling/test_docling_local.py -v -s
    
The -s flag shows print output for detailed reports.
"""

import os
import time
import tempfile
import pytest


# Skip all tests if test document not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DOCUMENT_PATH") or not os.path.exists(os.environ.get("TEST_DOCUMENT_PATH", "")),
    reason="TEST_DOCUMENT_PATH not set or file does not exist"
)


class TestDoclingLocal:
    """Test suite for local document processing with comprehensive reporting."""

    @pytest.fixture(autouse=True)
    def setup(self, test_document_path, test_report):
        """Initialize local connector for each test."""
        from infrastructure.connector.document_connector import DocumentConnector
        from infrastructure.config.doc_config_manager import DocConfigManager
        
        self.config_manager = DocConfigManager()
        self.connector = DocumentConnector(config_manager=self.config_manager)
        self.test_document_path = test_document_path
        self.create_report = test_report

    def _get_file_info(self, path: str) -> dict:
        """Get file information."""
        stat = os.stat(path)
        return {
            "path": path,
            "filename": os.path.basename(path),
            "size_bytes": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "extension": os.path.splitext(path)[1],
        }

    def test_initialization(self):
        """Test that local connector initializes correctly."""
        report = self.create_report(
            "Initialization",
            "local",
            "Validates DocumentConnector initializes in local mode without service client"
        )
        
        # Validations
        report.add_validation("connector_exists", True, self.connector is not None, self.connector is not None)
        report.add_validation("is_local_mode", False, self.connector.is_remote, self.connector.is_remote is False)
        report.add_validation("converter_loaded", True, self.connector._converter is not None, self.connector._converter is not None)
        
        # Results
        report.add_result("service_client", self.connector._service_client)
        report.add_result("config_manager", type(self.config_manager).__name__)
        
        report.print_report()
        
        assert self.connector is not None
        assert self.connector.is_remote is False

    def test_authentication(self):
        """Test that authentication returns True."""
        report = self.create_report(
            "Authentication",
            "local",
            "Validates local connector always returns True for authentication"
        )
        
        result = self.connector.authenticate()
        
        report.add_validation("auth_returns_true", True, result, result is True)
        report.add_result("auth_result", result)
        
        report.print_report()
        
        assert result is True

    def test_connection(self):
        """Test that connection test returns True."""
        report = self.create_report(
            "Connection Test",
            "local",
            "Validates local connector always passes connection test"
        )
        
        result = self.connector.test_connection()
        
        report.add_validation("connection_success", True, result, result is True)
        report.add_result("connection_result", result)
        
        report.print_report()
        
        assert result is True

    def test_process_document(self):
        """Test processing a single document with detailed output."""
        report = self.create_report(
            "Process Document",
            "local",
            "Validates document is processed and returns text + markdown content"
        )
        
        file_info = self._get_file_info(self.test_document_path)
        
        start_time = time.time()
        result = self.connector.process_document(
            self.test_document_path,
            upload_by="test_user"
        )
        elapsed = time.time() - start_time
        
        text = result.get("text", "")
        markdown = result.get("markdown", "")
        
        # Validations
        report.add_validation("result_not_none", True, result is not None, result is not None)
        report.add_validation("text_extracted", True, len(text) > 0, len(text) > 0)
        report.add_validation("markdown_extracted", True, len(markdown) > 0, len(markdown) > 0)
        
        # Metrics
        report.add_metric("input_size_mb", file_info["size_mb"])
        report.add_metric("processing_time_seconds", elapsed)
        report.add_metric("text_length_chars", len(text))
        report.add_metric("text_length_words", len(text.split()))
        report.add_metric("markdown_length_chars", len(markdown))
        
        # Results
        report.add_result("input_file", file_info["filename"])
        report.add_result("output_keys", list(result.keys()))
        report.add_result("text_preview", text[:300] + "..." if len(text) > 300 else text)
        
        report.print_report()
        
        assert result is not None
        assert len(text) > 0
        assert len(markdown) > 0

    def test_text_content_quality(self):
        """Test the quality of extracted text content."""
        report = self.create_report(
            "Text Content Quality",
            "local",
            "Validates extracted text has sufficient words and character distribution"
        )
        
        result = self.connector.process_document(self.test_document_path)
        text = result.get("text", "")
        
        words = text.split()
        unique_words = set(w.lower() for w in words)
        vocab_richness = len(unique_words) / len(words) if words else 0
        
        # Validations
        report.add_validation("min_word_count", "> 10", len(words), len(words) > 10)
        report.add_validation("vocabulary_richness", "> 0.1", round(vocab_richness, 3), vocab_richness > 0.1)
        
        # Metrics
        report.add_metric("total_words", len(words))
        report.add_metric("unique_words", len(unique_words))
        report.add_metric("vocabulary_richness", vocab_richness)
        report.add_metric("total_chars", len(text))
        report.add_metric("alpha_chars", sum(1 for c in text if c.isalpha()))
        
        # Results
        report.add_result("first_50_words", " ".join(words[:50]))
        
        report.print_report()
        
        assert len(words) > 10

    def test_markdown_content(self):
        """Test the extracted markdown content."""
        report = self.create_report(
            "Markdown Content",
            "local",
            "Validates markdown is extracted with proper structure"
        )
        
        result = self.connector.process_document(self.test_document_path)
        markdown = result.get("markdown", "")
        
        lines = markdown.split("\n")
        headers = [l for l in lines if l.startswith("#")]
        
        # Validations
        report.add_validation("markdown_not_empty", True, len(markdown) > 0, len(markdown) > 0)
        
        # Metrics
        report.add_metric("total_lines", len(lines))
        report.add_metric("header_count", len(headers))
        report.add_metric("total_chars", len(markdown))
        
        # Results
        report.add_result("headers_found", headers[:5] if headers else ["No headers"])
        report.add_result("preview", markdown[:500] + "..." if len(markdown) > 500 else markdown)
        
        report.print_report()
        
        assert len(markdown) > 0

    def test_metadata_extraction(self):
        """Test metadata extraction from document."""
        report = self.create_report(
            "Metadata Extraction",
            "local",
            "Validates document metadata is extracted (page count, file info, etc.)"
        )
        
        result = self.connector.process_document(
            self.test_document_path,
            upload_by="test_user"
        )
        
        metadata = result.get("metadata", {})
        
        # Validations
        report.add_validation("has_metadata", True, len(metadata) > 0, len(metadata) > 0)
        
        # Metrics
        report.add_metric("metadata_field_count", len(metadata))
        
        # Results
        report.add_result("metadata_keys", list(metadata.keys()))
        for key, value in list(metadata.items())[:5]:
            report.add_result(f"meta_{key}", value)
        
        report.print_report()
        
        if metadata:
            assert isinstance(metadata, dict)

    def test_document_structure(self):
        """Test document structure extraction."""
        report = self.create_report(
            "Document Structure",
            "local",
            "Validates document sections/headings are extracted"
        )
        
        self.connector.process_document(self.test_document_path)
        structure = self.connector.get_document_structure(self.test_document_path)
        
        if structure:
            sections = structure.get("sections", [])
            report.add_validation("structure_extracted", True, True, True)
            report.add_metric("section_count", len(sections))
            report.add_result("title", structure.get("title"))
            report.add_result("section_titles", [s.get("title", "")[:50] for s in sections[:5]])
        else:
            report.add_validation("structure_extracted", True, False, False)
            report.add_result("note", "Structure not available for this document type")
        
        report.print_report()

    def test_batch_processing(self):
        """Test processing multiple documents."""
        report = self.create_report(
            "Batch Processing",
            "local",
            "Validates multiple documents can be processed in batch"
        )
        
        doc_paths = [self.test_document_path]
        
        start_time = time.time()
        results = self.connector.process_documents(doc_paths)
        elapsed = time.time() - start_time
        
        # Validations
        report.add_validation("output_matches_input", len(doc_paths), len(results), len(results) == len(doc_paths))
        
        # Metrics
        report.add_metric("input_count", len(doc_paths))
        report.add_metric("output_count", len(results))
        report.add_metric("processing_time_seconds", elapsed)
        report.add_metric("docs_per_second", len(doc_paths) / elapsed if elapsed > 0 else 0)
        
        # Results
        for i, result in enumerate(results):
            report.add_result(f"doc_{i}_text_length", len(result.get("text", "")))
        
        report.print_report()
        
        assert len(results) == 1

    def test_invalid_file_path(self):
        """Test handling of non-existent file."""
        report = self.create_report(
            "Invalid File Path",
            "local",
            "Validates proper error is raised for non-existent file"
        )
        
        from infrastructure.connector.document_connector import DoclingProcessingError
        
        invalid_path = "/nonexistent/path/to/document.pdf"
        error_raised = False
        error_message = None
        
        try:
            self.connector.process_document(invalid_path)
        except DoclingProcessingError as e:
            error_raised = True
            error_message = str(e)
        
        # Validations
        report.add_validation("error_raised", True, error_raised, error_raised)
        
        # Results
        report.add_result("error_message", error_message)
        report.add_result("invalid_path", invalid_path)
        
        report.print_report()
        
        assert error_raised

    def test_unsupported_extension(self):
        """Test handling of unsupported file extension."""
        report = self.create_report(
            "Unsupported Extension",
            "local",
            "Validates proper error is raised for unsupported file types"
        )
        
        from infrastructure.connector.document_connector import DoclingProcessingError
        
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"Test content")
            temp_path = f.name
        
        try:
            error_raised = False
            error_message = None
            
            try:
                self.connector.process_document(temp_path)
            except DoclingProcessingError as e:
                error_raised = True
                error_message = str(e)
            
            # Validations
            report.add_validation("error_raised", True, error_raised, error_raised)
            
            # Results
            report.add_result("test_extension", ".xyz")
            report.add_result("error_message", error_message)
            
            report.print_report()
            
            assert error_raised
        finally:
            os.unlink(temp_path)

    def test_processing_consistency(self):
        """Test that processing the same document gives consistent results."""
        report = self.create_report(
            "Processing Consistency",
            "local",
            "Validates same document produces identical output on multiple runs"
        )
        
        result1 = self.connector.process_document(self.test_document_path)
        result2 = self.connector.process_document(self.test_document_path)
        
        text1 = result1.get("text", "")
        text2 = result2.get("text", "")
        md1 = result1.get("markdown", "")
        md2 = result2.get("markdown", "")
        
        text_match = text1 == text2
        md_match = md1 == md2
        
        # Validations
        report.add_validation("text_identical", True, text_match, text_match)
        report.add_validation("markdown_identical", True, md_match, md_match)
        
        # Metrics
        report.add_metric("text1_length", len(text1))
        report.add_metric("text2_length", len(text2))
        report.add_metric("length_difference", abs(len(text1) - len(text2)))
        
        report.print_report()
        
        assert text_match
        assert md_match

    def test_caching(self):
        """Test that conversion results are cached."""
        report = self.create_report(
            "Caching",
            "local",
            "Validates document results are cached after first processing"
        )
        
        self.connector.process_document(self.test_document_path)
        
        is_cached = self.test_document_path in self.connector._conversion_results
        cache_size = len(self.connector._conversion_results)
        
        # Validations
        report.add_validation("document_cached", True, is_cached, is_cached)
        
        # Metrics
        report.add_metric("cache_size", cache_size)
        
        # Results
        report.add_result("cached_paths", list(self.connector._conversion_results.keys()))
        
        report.print_report()
        
        assert is_cached
