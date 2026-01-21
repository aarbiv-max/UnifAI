"""
Pytest configuration and shared fixtures for UnifAI tests.

Environment Variables:
    EMBEDDING_SERVICE_URL     - Remote embedding service URL
    EMBEDDING_SERVICE_TIMEOUT - Timeout in seconds (default: 60)
    EMBEDDING_MODEL_NAME      - Model name (default: all-MiniLM-L6-v2)
    
    DOCLING_SERVICE_URL       - Remote docling service URL
    DOCLING_SERVICE_TIMEOUT   - Timeout in seconds (default: 300)
    TEST_DOCUMENT_PATH        - Path to test PDF document
"""

import os
import sys
import json
import pytest
from datetime import datetime
from typing import Dict, Any, List

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "global_utils", "src"))


class TestReport:
    """Collects and formats test results with clear status reporting."""
    
    def __init__(self, test_name: str, mode: str, description: str = ""):
        self.test_name = test_name
        self.mode = mode  # "local" or "remote"
        self.description = description
        self.timestamp = datetime.now().isoformat()
        self.status = "PASS"  # Default to PASS
        self.reason = ""  # Reason for failure
        self.metrics: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        self.validations: List[Dict[str, Any]] = []
    
    def set_description(self, description: str):
        """Set test description."""
        self.description = description
    
    def add_metric(self, name: str, value: Any):
        """Add a metric to the report."""
        self.metrics[name] = value
    
    def add_result(self, name: str, value: Any):
        """Add a result to the report."""
        self.results[name] = value
    
    # Alias for backward compatibility
    def add_detail(self, name: str, value: Any):
        """Add a result/detail to the report."""
        self.results[name] = value
    
    def add_validation(self, check: str, expected: Any, actual: Any, passed: bool):
        """Add a validation check result."""
        self.validations.append({
            "check": check,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        })
        if not passed:
            self.status = "FAIL"
            self.reason = f"{check}: expected {expected}, got {actual}"
    
    def set_failed(self, reason: str):
        """Mark test as failed with reason."""
        self.status = "FAIL"
        self.reason = reason
    
    def print_report(self):
        """Print formatted report to stdout."""
        # Header
        print("\n" + "=" * 80)
        print(f"  TEST: {self.test_name}")
        print("=" * 80)
        
        # Basic info
        print(f"  Mode:        {self.mode.upper()}")
        print(f"  Timestamp:   {self.timestamp}")
        
        if self.description:
            print(f"  Description: {self.description}")
        
        # Status with visual indicator
        if self.status == "PASS":
            print(f"  Status:      ✓ PASS")
        else:
            print(f"  Status:      ✗ FAIL")
            print(f"  Reason:      {self.reason}")
        
        print("-" * 80)
        
        # Metrics section
        if self.metrics:
            print("  METRICS:")
            for name, value in self.metrics.items():
                if isinstance(value, float):
                    print(f"    • {name}: {value:.4f}")
                elif isinstance(value, bool):
                    print(f"    • {name}: {'✓ Yes' if value else '✗ No'}")
                else:
                    print(f"    • {name}: {value}")
            print()
        
        # Results section
        if self.results:
            print("  RESULTS:")
            for name, value in self.results.items():
                if isinstance(value, str) and len(value) > 80:
                    print(f"    • {name}:")
                    print(f"      {value[:80]}...")
                elif isinstance(value, list) and len(value) > 3:
                    print(f"    • {name}: [{len(value)} items]")
                    for i, item in enumerate(value[:2]):
                        item_str = str(item)[:60] + "..." if len(str(item)) > 60 else str(item)
                        print(f"        [{i}]: {item_str}")
                    print(f"        ... and {len(value) - 2} more")
                elif isinstance(value, dict):
                    print(f"    • {name}:")
                    for k, v in list(value.items())[:5]:
                        v_str = str(v)[:50] + "..." if len(str(v)) > 50 else str(v)
                        print(f"        {k}: {v_str}")
                else:
                    print(f"    • {name}: {value}")
            print()
        
        # Validations section
        if self.validations:
            print("  VALIDATIONS:")
            for v in self.validations:
                icon = "✓" if v["passed"] else "✗"
                print(f"    {icon} {v['check']}: expected={v['expected']}, actual={v['actual']}")
            print()
        
        print("=" * 80 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "test_name": self.test_name,
            "mode": self.mode,
            "description": self.description,
            "timestamp": self.timestamp,
            "status": self.status,
            "reason": self.reason,
            "metrics": self.metrics,
            "results": self.results,
            "validations": self.validations,
        }
    
    def to_json(self) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


@pytest.fixture
def embedding_service_url():
    """Get embedding service URL from environment."""
    return os.environ.get("EMBEDDING_SERVICE_URL", "http://localhost:5002")


@pytest.fixture
def embedding_service_timeout():
    """Get embedding service timeout from environment."""
    return int(os.environ.get("EMBEDDING_SERVICE_TIMEOUT", "60"))


@pytest.fixture
def embedding_model_name():
    """Get embedding model name from environment."""
    return os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")


@pytest.fixture
def docling_service_url():
    """Get docling service URL from environment."""
    return os.environ.get("DOCLING_SERVICE_URL", "http://localhost:5001")


@pytest.fixture
def docling_service_timeout():
    """Get docling service timeout from environment."""
    return int(os.environ.get("DOCLING_SERVICE_TIMEOUT", "300"))


@pytest.fixture
def test_document_path():
    """Get test document path from environment."""
    path = os.environ.get("TEST_DOCUMENT_PATH")
    if path and os.path.exists(path):
        return path
    return None


@pytest.fixture
def sample_texts():
    """Sample texts for embedding tests."""
    return [
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning uses neural networks with many layers.",
        "Natural language processing enables computers to understand text.",
        "Computer vision allows machines to interpret images.",
        "Reinforcement learning trains agents through rewards.",
    ]


@pytest.fixture
def sample_chunks(sample_texts):
    """Sample chunks for batch embedding tests."""
    return [{"text": text, "id": str(i)} for i, text in enumerate(sample_texts)]


@pytest.fixture
def test_report():
    """Factory fixture for creating test reports."""
    def _create_report(test_name: str, mode: str, description: str = "") -> TestReport:
        return TestReport(test_name, mode, description)
    return _create_report


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "local: mark test as local mode test")
    config.addinivalue_line("markers", "remote: mark test as remote mode test")
