"""
Tests for hybrid_search and search_knowledge fusion (Chroma + BM25 + RRF).

Run from this directory:
  ./Python/bin/python test_hybrid_search.py

Requires: rank-bm25 (pip install rank-bm25)
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from typing import List

# ---------------------------------------------------------------------------
# Unit tests: hybrid_search only (no mcp_server import order constraints)
# ---------------------------------------------------------------------------


class TestHybridSearchUnit(unittest.TestCase):
    def test_reciprocal_rank_fusion(self) -> None:
        from hybrid_search import reciprocal_rank_fusion

        s = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a"]], k=60.0)
        self.assertGreater(s["a"], s["c"])

    def test_stable_doc_id(self) -> None:
        from hybrid_search import STABLE_SEP, stable_doc_id

        sid = stable_doc_id("coll", {"source": "f.py", "chunk_index": 3}, "body")
        self.assertEqual(sid, f"coll{STABLE_SEP}f.py{STABLE_SEP}3")

    def test_search_bm25_ranked_ids_and_repo_filter(self) -> None:
        import chromadb
        from hybrid_search import (
            HYBRID_AVAILABLE,
            CachedBM25Index,
            search_bm25_ranked_ids,
        )

        if not HYBRID_AVAILABLE:
            self.skipTest("rank-bm25 not installed")

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        client = chromadb.PersistentClient(path=tmp)
        col = client.create_collection("demo")
        # Pre-supply embeddings so Chroma does not pull the default ONNX model (~79MB).
        # BM25Okapi returns all-zero scores for a 2-doc corpus; need >=3 rows for IDF.
        z = [0.01] * 8
        col.add(
            ids=["1", "2", "3"],
            documents=["alpha beta gamma", "alpha special token", "filler doc zero"],
            embeddings=[z, z, z],
            metadatas=[
                {"source": "a", "chunk_index": 0, "repository": "r1"},
                {"source": "b", "chunk_index": 0, "repository": "r2"},
                {"source": "c", "chunk_index": 0, "repository": "r1"},
            ],
        )
        idx = CachedBM25Index("demo", tmp)
        self.assertTrue(idx.ensure_loaded(col))
        sid_b = next(
            s
            for s in idx.ordered_ids
            if idx.id_to_doc.get(s, ("", {}))[1].get("source") == "b"
        )
        ranked = search_bm25_ranked_ids(idx, "special token", top_n=5, repo_filter="")
        self.assertEqual(ranked[0], sid_b)

        ranked_r1 = search_bm25_ranked_ids(idx, "special token", top_n=5, repo_filter="r1")
        self.assertNotIn(sid_b, ranked_r1)
        self.assertTrue(
            all(idx.id_to_doc[s][1].get("repository") == "r1" for s in ranked_r1),
            ranked_r1,
        )


# ---------------------------------------------------------------------------
# Integration: _sync_multi_search with constant embeddings (dense ties)
# ---------------------------------------------------------------------------


class _ConstantEmb:
    """Minimal embedding shim for Chroma (all vectors equal → dense order weak)."""

    dim = 8

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.02] * self.dim for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [0.02] * self.dim


class TestHybridMcpIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.mkdtemp()
        os.environ["DB_PATH"] = cls._tmpdir
        os.environ["HYBRID_SEARCH"] = "1"
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import hybrid_search as hs

        hs._index_singletons.clear()

        import mcp_server as ms  # noqa: E402 — after env

        cls._mcp = ms
        from hybrid_search import HYBRID_AVAILABLE

        if not HYBRID_AVAILABLE:
            raise unittest.SkipTest("rank-bm25 not installed")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_hybrid_prefers_bm25_when_dense_is_flat(self) -> None:
        from langchain_chroma import Chroma

        ms = self._mcp
        emb = _ConstantEmb()
        vs = Chroma(
            collection_name="multicast_code",
            persist_directory=self._tmpdir,
            embedding_function=emb,
        )
        vs.add_texts(
            texts=[
                "unrelated boilerplate and comments",
                "TAG_IGMP_V3 igmpInput group membership",
                "more generic networking stack glue",
            ],
            metadatas=[
                {"source": "x.c", "chunk_index": 0, "repository": "fw"},
                {"source": "igmp.c", "chunk_index": 1, "repository": "fw"},
                {"source": "y.c", "chunk_index": 2, "repository": "fw"},
            ],
            ids=["id0", "id1", "id2"],
        )
        cmap = {"multicast_code": vs}
        results = ms._sync_multi_search(
            "TAG_IGMP_V3 igmpInput",
            k=3,
            search_type="code",
            domain="general",
            repo_filter="",
            cmap=cmap,
        )
        self.assertTrue(results, "expected non-empty hybrid results")
        top = results[0][0].page_content
        self.assertIn("TAG_IGMP_V3", top)

    def test_hybrid_off_dense_only_path(self) -> None:
        """Dense-only branch: subprocess so HYBRID_SEARCH=0 is read at import."""
        import subprocess

        script = r"""
import os, sys, tempfile, shutil
t2 = tempfile.mkdtemp()
os.environ["DB_PATH"] = t2
os.environ["HYBRID_SEARCH"] = "0"
sys.path.insert(0, sys.argv[1])
from langchain_chroma import Chroma

class E:
    dim = 8
    def embed_documents(self, texts):
        return [[0.02] * self.dim for _ in texts]
    def embed_query(self, text):
        return [0.02] * self.dim

import mcp_server as ms
vs = Chroma(collection_name="other_code", persist_directory=t2, embedding_function=E())
vs.add_texts(
    texts=["aaa", "bbb"],
    metadatas=[{"source": "a.c", "chunk_index": 0}, {"source": "b.c", "chunk_index": 0}],
    ids=["a", "b"],
)
out = ms._sync_multi_search("bbb", 2, "code", "general", "", {"other_code": vs})
assert len(out) == 2, out
assert out[0][1] is not None, "dense-only should return distance scores"
shutil.rmtree(t2, ignore_errors=True)
print("ok")
"""
        root = os.path.dirname(os.path.abspath(__file__))
        r = subprocess.run(
            [sys.executable, "-c", script, root],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestHybridSearchUnit))
    suite.addTests(loader.loadTestsFromTestCase(TestHybridMcpIntegration))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
