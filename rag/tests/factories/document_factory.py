"""
DocumentFactory - factory for creating test PDF documents.

Wraps the existing DocumentGenerator from the standalone stress test script
and exposes a clean factory interface consistent with the multi-agent
NodeFactory / TaskFactory patterns.
"""

import random
import string
import time
from io import BytesIO
from datetime import datetime
from typing import List, Tuple


class DocumentFactory:
    """
    Factory for generating test PDF documents.

    Provides static methods for creating individual and batches of PDF
    documents used in RAG upload and embedding stress tests.
    """

    TOPICS = [
        "Artificial Intelligence", "Machine Learning", "Deep Learning",
        "Cloud Computing", "Blockchain Technology", "Quantum Computing",
        "Cybersecurity", "Internet of Things", "Big Data Analytics",
        "Natural Language Processing", "Computer Vision", "Robotics",
        "Edge Computing", "5G Networks", "Augmented Reality",
        "Virtual Reality", "DevOps", "Microservices", "Kubernetes",
        "Docker Containers", "Serverless Computing", "API Design",
        "Database Management", "Data Warehousing", "ETL Processes",
    ]

    @staticmethod
    def generate_content(doc_id: int, topic: str = None) -> str:
        """Generate unique textual content for a document.

        Args:
            doc_id: Numeric identifier used to seed unique values.
            topic: Optional topic override; random if not provided.

        Returns:
            Multi-paragraph string with unique content.
        """
        if topic is None:
            topic = random.choice(DocumentFactory.TOPICS)

        unique_id = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )

        content = (
            f"Document ID: {doc_id}\n"
            f"Unique Identifier: {unique_id}\n"
            f"Topic: {topic}\n"
            f"Generated: {datetime.now().isoformat()}\n\n"
            f"Introduction to {topic}\n"
            f"{'=' * 50}\n\n"
            f"This document discusses the fundamentals and advanced concepts of {topic}.\n"
            f"Each document in this stress test contains unique content to ensure proper\n"
            f"handling of distinct documents by the system.\n\n"
            f"Section 1: Overview\n"
            f"{'-' * 30}\n"
            f"{topic} represents a significant advancement in modern technology.\n"
            f"Random data: {random.random()}\n"
            f"Timestamp: {time.time()}\n\n"
        )

        for i in range(5):
            content += (
                f"Section {i + 2}: Detailed Analysis Part {i + 1}\n"
                f"{'-' * 30}\n"
                f"This section contains unique information about {topic} with random data:\n"
                f"{''.join(random.choices(string.ascii_letters, k=200))}\n\n"
                f"Key Points:\n"
                f"- Point 1: Random value {random.randint(1000, 9999)}\n"
                f"- Point 2: Unique timestamp {time.time()}\n"
                f"- Point 3: Random string {unique_id[:8]}\n\n"
            )

        return content

    @staticmethod
    def create_pdf(doc_id: int, filename: str) -> bytes:
        """Create a 2-page PDF document with unique content.

        Uses ReportLab to generate a real PDF binary. Falls back to a plain
        text byte string when ReportLab is not installed (useful for unit
        tests that do not need a real PDF).

        Args:
            doc_id: Numeric identifier embedded in the document.
            filename: Filename string embedded in the document title.

        Returns:
            Raw PDF bytes.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
            )

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
            )

            story = []
            story.append(
                Paragraph(f"Stress Test Document #{doc_id}", title_style)
            )
            story.append(Spacer(1, 0.2 * inch))

            content = DocumentFactory.generate_content(doc_id)
            paragraphs = content.split("\n\n")
            mid = len(paragraphs) // 2

            for para in paragraphs[:mid]:
                if para.strip():
                    story.append(Paragraph(para.strip(), styles["Normal"]))
                    story.append(Spacer(1, 0.1 * inch))

            story.append(PageBreak())

            story.append(
                Paragraph(f"Document #{doc_id} - Page 2", styles["Heading2"])
            )
            story.append(Spacer(1, 0.2 * inch))

            for para in paragraphs[mid:]:
                if para.strip():
                    story.append(Paragraph(para.strip(), styles["Normal"]))
                    story.append(Spacer(1, 0.1 * inch))

            story.append(Spacer(1, 0.3 * inch))
            story.append(
                Paragraph(
                    f"Unique ID: {time.time()}-{doc_id}-{random.randint(10000, 99999)}",
                    styles["Normal"],
                )
            )

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes

        except ImportError:
            # Fallback: plain text bytes (sufficient for unit/mock tests)
            content = DocumentFactory.generate_content(doc_id)
            return content.encode("utf-8")

    @staticmethod
    def make_filename(doc_id: int, prefix: str = "stress_test_doc") -> str:
        """Return a standardised filename for a test document.

        Args:
            doc_id: Numeric document index.
            prefix: Filename prefix.

        Returns:
            Filename string, e.g. ``stress_test_doc_001.pdf``.
        """
        return f"{prefix}_{doc_id:03d}.pdf"

    @staticmethod
    def create_batch(
        count: int,
        start_id: int = 1,
        prefix: str = "stress_test_doc",
    ) -> List[Tuple[int, str, bytes]]:
        """Create a batch of PDF documents.

        Args:
            count: Number of documents to generate.
            start_id: First document ID (default 1).
            prefix: Filename prefix for all documents in the batch.

        Returns:
            List of ``(doc_id, filename, pdf_bytes)`` tuples.
        """
        batch = []
        for i in range(start_id, start_id + count):
            filename = DocumentFactory.make_filename(i, prefix)
            pdf_bytes = DocumentFactory.create_pdf(i, filename)
            batch.append((i, filename, pdf_bytes))
        return batch
