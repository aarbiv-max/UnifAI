from typing import Any, Set
from pydantic import BaseModel
from core.ref.models import Ref


class RefWalker:
    """
    Pure utility: depth-first traversal that returns the set of external
    resource IDs (rid strings) found in an object graph.
    """

    @staticmethod
    def external_rids(root: Any) -> Set[str]:
        bucket: set[str] = set()
        RefWalker._walk(root, bucket)
        return bucket

    @staticmethod
    def _walk(node: Any, bucket: set[str]) -> None:
        if isinstance(node, Ref):
            if node.is_external_ref():
                bucket.add(node.ref)
            return

        if isinstance(node, BaseModel):
            for v in node.__dict__.values():
                RefWalker._walk(v, bucket)
            return

        if isinstance(node, dict):
            for v in node.values():
                RefWalker._walk(v, bucket)
            return

        if isinstance(node, (list, tuple)):
            for v in node:
                RefWalker._walk(v, bucket)
