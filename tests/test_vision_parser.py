"""parse_pdf_with_vision orchestration with stubbed Docling + VLM.

Docling itself is optional and heavy; these tests inject minimal fake
docling modules so the event stream, ordering, and parallel captioning
logic run hermetically.
"""
from __future__ import annotations

import sys
import threading
import time
import types
from typing import Any, List

import pytest

from util import universal_vision_parser as uvp


class _FakePicture:
    def __init__(self, image: Any):
        self._image = image

    def get_image(self, _document: Any) -> Any:
        return self._image


class _FakeTextItem:
    def __init__(self, text: str):
        self.text = text


class _FakeDoc:
    def __init__(self, items: List[Any]):
        self._items = items

    def iterate_items(self):
        return [(it, 0) for it in self._items]


def _install_fake_docling(monkeypatch: pytest.MonkeyPatch, document: _FakeDoc) -> None:
    class _ConvResult:
        pass

    class _FakeConverter:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def convert(self, _path: str) -> Any:
            r = _ConvResult()
            r.document = document
            return r

    class _Serialized:
        def __init__(self, text: str):
            self.text = text

    class _FakeSerializer:
        def __init__(self, doc: Any) -> None:
            self._doc = doc

        def serialize(self, item: Any) -> Any:
            return _Serialized(getattr(item, "text", ""))

    mods = {
        "docling": types.ModuleType("docling"),
        "docling.document_converter": types.ModuleType("docling.document_converter"),
        "docling.datamodel": types.ModuleType("docling.datamodel"),
        "docling.datamodel.base_models": types.ModuleType("docling.datamodel.base_models"),
        "docling.datamodel.pipeline_options": types.ModuleType("docling.datamodel.pipeline_options"),
        "docling.document": types.ModuleType("docling.document"),
        "docling.document.datamodel": types.ModuleType("docling.document.datamodel"),
        "docling_core": types.ModuleType("docling_core"),
        "docling_core.transforms": types.ModuleType("docling_core.transforms"),
        "docling_core.transforms.serializer": types.ModuleType("docling_core.transforms.serializer"),
        "docling_core.transforms.serializer.markdown": types.ModuleType(
            "docling_core.transforms.serializer.markdown"
        ),
    }
    mods["docling.document_converter"].DocumentConverter = _FakeConverter
    mods["docling.document_converter"].PdfFormatOption = lambda **_k: object()
    mods["docling.datamodel.base_models"].InputFormat = types.SimpleNamespace(PDF="pdf")

    class _PipelineOptions:
        generate_picture_images = False

    mods["docling.datamodel.pipeline_options"].PdfPipelineOptions = _PipelineOptions
    mods["docling.document.datamodel"].PictureItem = _FakePicture
    mods["docling_core.transforms.serializer.markdown"].MarkdownDocSerializer = _FakeSerializer
    for name, mod in mods.items():
        monkeypatch.setitem(sys.modules, name, mod)


@pytest.fixture
def fake_pdf(tmp_path):
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-fake")
    return p


def _run(monkeypatch, fake_pdf, document, provider="anthropic", workers="4", captioner=None):
    _install_fake_docling(monkeypatch, document)
    monkeypatch.setenv("VISION_CAPTION_WORKERS", workers)
    monkeypatch.setattr(uvp, "encode_image_to_base64", lambda img: f"b64:{img}")
    if captioner is not None:
        monkeypatch.setattr(uvp, "_caption_image", captioner)
    return list(
        uvp.parse_pdf_with_vision(
            str(fake_pdf), vision_provider=provider, api_key="k", vision_model="m"
        )
    )


def test_vision_events_preserve_document_order(monkeypatch, fake_pdf):
    doc = _FakeDoc(
        [
            _FakeTextItem("intro"),
            _FakePicture("img1"),
            _FakeTextItem("middle"),
            _FakePicture("img2"),
        ]
    )

    def captioner(b64, **_kw):
        return f"caption-for-{b64}"

    events = _run(monkeypatch, fake_pdf, doc, captioner=captioner)
    complete = events[-1]
    assert complete["type"] == "complete"
    assert complete["total_images"] == 2
    md = complete["markdown"]
    # document order preserved: intro, caption img1, middle, caption img2
    assert md.index("intro") < md.index("caption-for-b64:img1") < md.index("middle") < md.index(
        "caption-for-b64:img2"
    )
    captions = [e for e in events if e["type"] == "image_caption"]
    assert [c["index"] for c in captions] == [1, 2]


def test_vision_cloud_captions_run_concurrently(monkeypatch, fake_pdf):
    doc = _FakeDoc([_FakePicture(f"img{i}") for i in range(4)])
    active = 0
    peak = 0
    lock = threading.Lock()

    def captioner(b64, **_kw):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.15)
        with lock:
            active -= 1
        return "c"

    events = _run(monkeypatch, fake_pdf, doc, workers="4", captioner=captioner)
    assert events[-1]["total_images"] == 4
    assert peak > 1, "cloud captions did not overlap"


def test_vision_ollama_stays_sequential(monkeypatch, fake_pdf):
    doc = _FakeDoc([_FakePicture(f"img{i}") for i in range(3)])
    active = 0
    peak = 0
    lock = threading.Lock()

    def captioner(b64, **_kw):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return "c"

    events = _run(monkeypatch, fake_pdf, doc, provider="ollama", workers="4", captioner=captioner)
    assert events[-1]["total_images"] == 3
    assert peak == 1


def test_vision_caption_failure_isolated(monkeypatch, fake_pdf):
    doc = _FakeDoc([_FakePicture("good"), _FakePicture("bad")])

    def captioner(b64, **_kw):
        if "bad" in b64:
            raise RuntimeError("vlm down")
        return "fine"

    events = _run(monkeypatch, fake_pdf, doc, captioner=captioner)
    md = events[-1]["markdown"]
    assert "fine" in md
    assert "Error generating caption" in md


def test_vision_extraction_failure_block(monkeypatch, fake_pdf):
    doc = _FakeDoc([_FakePicture(None)])  # get_image returns None
    events = _run(monkeypatch, fake_pdf, doc, captioner=lambda *_a, **_k: "x")
    md = events[-1]["markdown"]
    assert "DIAGRAM EXTRACTION FAILED" in md
    assert events[-1]["total_images"] == 0
