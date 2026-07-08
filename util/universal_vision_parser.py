"""
Vision-augmented PDF → Markdown using Docling layout + VLM captions for figures.

Library entry point: ``parse_pdf_with_vision`` (generator of progress events).
CLI: ``python -m util.universal_vision_parser --help``
"""
from __future__ import annotations

import argparse
import base64
import logging
import sys
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

log = logging.getLogger(__name__)

# Cloud VLM clients are cached per (provider, api_key): building a new SDK
# client per figure paid a fresh TLS handshake for every image in the PDF.
_client_cache: Dict[Tuple[str, str], Any] = {}
_client_cache_lock = threading.Lock()


def _cached_client(provider: str, api_key: str) -> Any:
    key = (provider, api_key)
    with _client_cache_lock:
        client = _client_cache.get(key)
        if client is None:
            if provider == "anthropic":
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
            else:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
            _client_cache[key] = client
        return client

DEFAULT_PROMPT = (
    "You are an expert Principal Electrical Engineer. Analyze this circuit diagram or graph. "
    "1. Identify the core topology. "
    "2. List the key components shown (MOSFETs, ICs, inductors, etc). "
    "3. Describe the critical connections and signal flow. "
    "4. If it is a graph, summarize the axes and the key takeaway. "
    "Do not use introductory phrases. Be extremely detailed, highly technical, and strictly factual."
)

DEFAULT_MODELS = {
    "ollama": "llama3.2-vision",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


def check_vision_dependencies() -> Dict[str, bool]:
    """Return which optional deps are importable."""
    docling_ok = False
    pillow_ok = False
    try:
        from docling.document_converter import DocumentConverter  # noqa: F401

        docling_ok = True
    except ImportError:
        pass
    try:
        from PIL import Image  # noqa: F401

        pillow_ok = True
    except ImportError:
        pass
    return {"docling_available": docling_ok, "pillow_available": pillow_ok}


def encode_image_to_base64(pil_image: Any) -> str:
    buffered = BytesIO()
    pil_image.convert("RGB").save(buffered, format="JPEG", quality=95)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def _blockquote_lines(text: str, prefix: str = "> ") -> str:
    lines = (text or "").strip().splitlines()
    if not lines:
        return prefix.rstrip()
    return "\n".join(prefix + (line if line else "") for line in lines)


def _caption_image(
    image_b64: str,
    *,
    vision_provider: str,
    vision_model: str,
    api_key: str,
    prompt: str,
) -> str:
    provider = (vision_provider or "ollama").strip().lower()
    model = (vision_model or "").strip()
    if not model:
        model = DEFAULT_MODELS.get(provider, DEFAULT_MODELS["ollama"])

    if provider == "ollama":
        import ollama

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "user", "content": prompt, "images": [image_b64]},
            ],
            options={"temperature": 0.1},
        )
        return (response.get("message") or {}).get("content", "").strip()

    if provider == "anthropic":
        if not api_key.strip():
            raise ValueError("Anthropic API key is required")

        client = _cached_client("anthropic", api_key.strip())
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        return "\n".join(parts).strip()

    if provider == "openai":
        if not api_key.strip():
            raise ValueError("OpenAI API key is required")

        client = _cached_client("openai", api_key.strip())
        response = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                            },
                        },
                    ],
                }
            ],
        )
        msg = response.choices[0].message
        return (msg.content or "").strip()

    raise ValueError(f"Unknown vision_provider: {vision_provider!r}")


def parse_pdf_with_vision(
    pdf_path: str,
    *,
    vision_provider: str = "ollama",
    vision_model: str = "",
    api_key: str = "",
    custom_prompt: str = "",
) -> Iterator[Dict[str, Any]]:
    """
    Parse a PDF with Docling; caption each figure via a VLM.

    Yields event dicts:
      - {"type": "status", "message": str}
      - {"type": "progress", "current": int, "total": int, "message": str}
      - {"type": "image_caption", "index": int, "caption": str}
      - {"type": "markdown_chunk", "text": str}
      - {"type": "complete", "total_images": int, "markdown": str, "elapsed_sec": float}
      - {"type": "error", "message": str}
    """
    deps = check_vision_dependencies()
    if not deps["pillow_available"]:
        yield {"type": "error", "message": "Pillow is not installed (pip install Pillow)."}
        return
    if not deps["docling_available"]:
        yield {
            "type": "error",
            "message": "Docling is not installed (pip install docling).",
        }
        return

    path = Path(pdf_path)
    if not path.is_file():
        yield {"type": "error", "message": f"PDF not found: {pdf_path}"}
        return

    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document.datamodel import PictureItem
    from docling_core.transforms.serializer.markdown import MarkdownDocSerializer

    prompt = (custom_prompt or "").strip() or DEFAULT_PROMPT
    provider_u = (vision_provider or "ollama").strip().lower()

    yield {
        "type": "status",
        "message": f"Loading PDF with Docling: {path.name}",
    }
    t0 = time.time()

    try:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.generate_picture_images = True

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        conv_result = converter.convert(str(path))
        document = conv_result.document
    except Exception as exc:
        log.exception("Docling convert failed")
        yield {"type": "error", "message": f"Docling failed to read PDF: {exc}"}
        return

    try:
        items: List[Tuple[Any, int]] = list(document.iterate_items())
    except Exception as exc:
        yield {"type": "error", "message": f"Failed to iterate document: {exc}"}
        return

    total_pictures = sum(1 for item, _ in items if isinstance(item, PictureItem))
    yield {
        "type": "status",
        "message": f"Found {total_pictures} image(s) / figures to caption via {provider_u}.",
    }

    markdown_lines: List[str] = []
    image_done = 0
    picture_index = 0
    md_serializer = MarkdownDocSerializer(doc=document)

    for item, _level in items:
        if isinstance(item, PictureItem):
            picture_index += 1
            if total_pictures > 0:
                yield {
                    "type": "progress",
                    "current": picture_index,
                    "total": total_pictures,
                    "message": f"Figure {picture_index}/{total_pictures}…",
                }

            img_pil = None
            try:
                img_pil = item.get_image(document)
            except Exception as exc:
                log.warning("get_image failed: %s", exc)

            if img_pil:
                image_done += 1
                try:
                    b64_img = encode_image_to_base64(img_pil)
                    caption = _caption_image(
                        b64_img,
                        vision_provider=provider_u,
                        vision_model=vision_model,
                        api_key=api_key,
                        prompt=prompt,
                    )
                except Exception as exc:
                    log.exception("VLM caption failed")
                    caption = f"[Error generating caption: {exc}]"

                header = f"\n> **[SCHEMATIC / DIAGRAM ANALYSIS ({provider_u.upper()})]**"
                quoted = _blockquote_lines(caption)
                block = f"{header}\n{quoted}\n"
                markdown_lines.append(block)
                yield {"type": "image_caption", "index": image_done, "caption": caption}
                yield {"type": "markdown_chunk", "text": block}
            else:
                fail_block = "\n> **[DIAGRAM EXTRACTION FAILED]**\n"
                markdown_lines.append(fail_block)
                yield {"type": "markdown_chunk", "text": fail_block}
        else:
            try:
                chunk = md_serializer.serialize(item=item).text
            except Exception as exc:
                log.warning("Markdown serialize failed for item: %s", exc)
                chunk = f"\n<!-- markdown serialize failed: {exc} -->\n"
            markdown_lines.append(chunk)
            yield {"type": "markdown_chunk", "text": chunk}

    final_markdown = "\n".join(markdown_lines)
    elapsed = time.time() - t0
    yield {
        "type": "complete",
        "total_images": image_done,
        "markdown": final_markdown,
        "elapsed_sec": round(elapsed, 2),
    }


def parse_datasheet_with_vision(pdf_path: str, output_path: str, **kwargs: Any) -> None:
    """Backward-compatible helper: stream events to console and write final markdown."""
    print(f"[*] Vision parsing: {pdf_path}")
    final_md = ""
    for ev in parse_pdf_with_vision(pdf_path, **kwargs):
        t = ev.get("type")
        if t == "status":
            print(f"    {ev.get('message', '')}")
        elif t == "progress":
            print(f"    {ev.get('message', '')}")
        elif t == "error":
            print(f"[-] {ev.get('message', '')}")
            return
        elif t == "complete":
            final_md = ev.get("markdown", "")
    Path(output_path).write_text(final_md, encoding="utf-8")
    print(f"[+] Wrote {output_path}")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Vision-augmented PDF → Markdown (Docling + VLM)")
    p.add_argument("pdf", help="Input PDF path")
    p.add_argument("-o", "--output", required=True, help="Output markdown path")
    p.add_argument(
        "--provider",
        choices=("ollama", "anthropic", "openai"),
        default="ollama",
    )
    p.add_argument("--model", default="", help="Override default model for provider")
    p.add_argument("--api-key", default="", help="API key (anthropic/openai); else env")
    p.add_argument("--prompt", default="", help="Override default caption prompt")
    args = p.parse_args(argv)

    key = args.api_key
    if args.provider == "anthropic" and not key:
        import os

        key = os.environ.get("ANTHROPIC_API_KEY", "")
    if args.provider == "openai" and not key:
        import os

        key = os.environ.get("OPENAI_API_KEY", "")

    parse_datasheet_with_vision(
        args.pdf,
        args.output,
        vision_provider=args.provider,
        vision_model=args.model,
        api_key=key,
        custom_prompt=args.prompt,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
