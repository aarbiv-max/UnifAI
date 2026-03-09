"""Unit tests for document validators and the DocValidators factory."""
from unittest.mock import MagicMock, patch

import pytest

from core.data_sources.types.document.validators.extension_validator import ExtensionValidator
from core.data_sources.types.document.validators.size_validator import SizeValidator, DEFAULT_MAX_FILE_SIZE_BYTES
from core.data_sources.types.document.validators.duplicate_validator import DuplicateValidator
from core.data_sources.types.document.validators.name_duplicate_validator import NameDuplicateValidator
from core.data_sources.types.document.validators.factory import DocValidators


SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".pptx", ".md", ".txt"]


# ═══════════════════════════════════════════════════════════════════════════════
# ExtensionValidator
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestExtensionValidator:

    @pytest.fixture
    def validator(self):
        return ExtensionValidator(supported_extensions=SUPPORTED_EXTENSIONS)

    @pytest.mark.parametrize("filename", [
        "report.pdf",
        "REPORT.PDF",
        "notes.docx",
        "slide.pptx",
        "readme.md",
        "log.txt",
    ])
    def test_valid_extensions_pass(self, validator, filename):
        ok, issue = validator.validate(source_name=filename)
        assert ok is True
        assert issue is None

    @pytest.mark.parametrize("filename,expected_ext", [
        ("malware.exe", ".exe"),
        ("image.zip", ".zip"),
        ("data.csv", ".csv"),
    ])
    def test_unsupported_extensions_rejected(self, validator, filename, expected_ext):
        ok, issue = validator.validate(source_name=filename)
        assert ok is False
        assert issue is not None
        assert "not supported" in issue["message"]
        assert expected_ext in issue["message"]

    def test_no_extension_rejected(self, validator):
        ok, issue = validator.validate(source_name="readme")
        assert ok is False
        assert issue is not None

    def test_empty_filename_passes(self, validator):
        ok, issue = validator.validate(source_name="")
        assert ok is True
        assert issue is None

    def test_issue_contains_supported_types(self, validator):
        ok, issue = validator.validate(source_name="image.zip")
        assert ok is False
        for ext in SUPPORTED_EXTENSIONS:
            assert ext in issue["message"]


# ═══════════════════════════════════════════════════════════════════════════════
# SizeValidator
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestSizeValidator:

    @pytest.fixture
    def validator(self):
        return SizeValidator()

    def test_file_under_limit_passes(self, tmp_path, validator):
        f = tmp_path / "small.pdf"
        f.write_bytes(b"x" * 1024)
        ok, issue = validator.validate(doc_path=str(f))
        assert ok is True
        assert issue is None

    @pytest.mark.parametrize("file_size,max_bytes,expected_ok", [
        (1025, 1024, False),
        (2048, 2048, True),
        (600, 500, False),
    ])
    def test_size_boundary(self, tmp_path, file_size, max_bytes, expected_ok):
        validator = SizeValidator(max_file_size_bytes=max_bytes)
        f = tmp_path / "boundary.pdf"
        f.write_bytes(b"x" * file_size)
        ok, issue = validator.validate(doc_path=str(f))
        assert ok is expected_ok
        if not expected_ok:
            assert issue is not None
            assert "exceeds" in issue["message"]

    def test_nonexistent_file_passes(self, validator):
        ok, issue = validator.validate(doc_path="/no/such/file.pdf")
        assert ok is True
        assert issue is None

    @patch("os.path.getsize", side_effect=OSError("disk error"))
    @patch("os.path.exists", return_value=True)
    def test_os_error_passes_gracefully(self, _mock_exists, _mock_size, validator):
        ok, issue = validator.validate(doc_path="/some/path.pdf")
        assert ok is True
        assert issue is None


# ═══════════════════════════════════════════════════════════════════════════════
# DuplicateValidator
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestDuplicateValidator:

    def _make_validator(self, is_dup=False, raises=None):
        checker = MagicMock()
        if raises:
            checker.is_duplicate.side_effect = raises
        else:
            checker.is_duplicate.return_value = is_dup
        return DuplicateValidator(duplicate_checker=checker)

    def test_not_duplicate_passes(self):
        validator = self._make_validator(is_dup=False)
        ok, issue = validator.validate(source_name="report.pdf")
        assert ok is True
        assert issue is None

    def test_duplicate_rejected(self):
        validator = self._make_validator(is_dup=True)
        ok, issue = validator.validate(source_name="report.pdf")
        assert ok is False
        assert issue is not None
        assert "report.pdf" in issue["message"]

    def test_checker_exception_passes_gracefully(self):
        validator = self._make_validator(raises=RuntimeError("db down"))
        ok, issue = validator.validate(source_name="report.pdf")
        assert ok is True
        assert issue is None


# ═══════════════════════════════════════════════════════════════════════════════
# NameDuplicateValidator
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestNameDuplicateValidator:

    def _make_validator(self, is_dup=False, status=None):
        checker = MagicMock()
        checker.is_duplicate_name.return_value = (is_dup, status)
        return NameDuplicateValidator(name_duplicate_checker=checker)

    def test_no_duplicate_passes(self):
        validator = self._make_validator(is_dup=False, status=None)
        ok, issue = validator.validate(source_name="new_doc.pdf", upload_by="alice")
        assert ok is True
        assert issue is None

    def test_duplicate_name_rejected(self):
        validator = self._make_validator(is_dup=True, status="DONE")
        ok, issue = validator.validate(source_name="existing.pdf", upload_by="alice")
        assert ok is False
        assert "existing.pdf" in issue["message"]
        assert "DONE" in issue["message"]

    def test_empty_source_name_passes(self):
        validator = self._make_validator(is_dup=True)
        ok, issue = validator.validate(source_name="", upload_by="alice")
        assert ok is True
        assert issue is None


# ═══════════════════════════════════════════════════════════════════════════════
# DocValidators factory
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestDocValidatorsFactory:

    @pytest.fixture
    def dup_mock(self):
        return MagicMock(spec=DuplicateValidator)

    @pytest.fixture
    def factory(self, dup_mock):
        return DocValidators(
            duplicate_validator=dup_mock,
            extension_validator=MagicMock(spec=ExtensionValidator),
            size_validator=MagicMock(spec=SizeValidator),
            name_duplicate_validator=MagicMock(spec=NameDuplicateValidator),
        )

    def test_full_validation_returns_all_four(self, factory):
        validators = factory.create_validators(skip_validation=False)
        assert len(validators) == 4

    def test_skip_validation_returns_only_duplicate(self, factory, dup_mock):
        validators = factory.create_validators(skip_validation=True)
        assert len(validators) == 1
        assert validators[0] is dup_mock
