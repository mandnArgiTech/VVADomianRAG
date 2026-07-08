#!/usr/bin/env python3
"""
Download RFCs as plain text from www.rfc-editor.org (authoritative mirror).

Example:
  python downloadrfc.py
  python downloadrfc.py --rfcs 793,7680 --output ./RFCs
  python downloadrfc.py --from-file rfcs.txt --force
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_RFCS = (1112, 2236, 3376, 4604, 5790, 7761, 8216, 9110, 9279, 9293, 9776)

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; DomainRAG-downloadrfc/1.0; +https://www.rfc-editor.org/)"
)


def _looks_like_rfc_text(raw: bytes) -> bool:
    if len(raw) < 200:
        return False
    head = raw[:800].lower()
    if b"<html" in head or b"<!doctype" in head:
        return False
    markers = (
        b"network working group",
        b"internet engineering task force",
        b"request for comments",
        b"rfc ",
        b"independent submission",
    )
    return any(m in head for m in markers)


def _parse_rfc_list(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            start, end = int(a), int(b)
            if end < start:
                raise ValueError(f"Invalid range {part!r} (end < start)")
            out.extend(range(start, end + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def _load_rfc_file(path: Path) -> list[int]:
    nums: list[int] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        nums.extend(_parse_rfc_list(line))
    return sorted(set(nums))


def fetch_rfc(
    num: int,
    dest: Path,
    *,
    force: bool,
    retries: int,
    timeout: float,
    user_agent: str,
    dry_run: bool,
    quiet: bool,
) -> tuple[str, str | None]:
    """
    Returns (status, error_message).
    status: 'ok' | 'skipped' | 'failed'
    """
    url = f"https://www.rfc-editor.org/rfc/rfc{num}.txt"
    if dest.exists() and not force:
        try:
            with dest.open("rb") as fh:  # only the head is inspected — skip full read
                head = fh.read(800)
        except OSError:
            head = b""
        if _looks_like_rfc_text(head):
            return "skipped", None
        # corrupt or HTML save — retry
    if dry_run:
        if not quiet:
            print(f"  [dry-run] would fetch {url} -> {dest}")
        return "ok", None

    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    last_err: str | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            if not _looks_like_rfc_text(raw):
                last_err = "response does not look like plain-text RFC"
                continue
            dest.write_bytes(raw)
            return "ok", None
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            last_err = str(e.reason if hasattr(e, "reason") else e)
        except TimeoutError:
            last_err = "timeout"
        except OSError as e:
            last_err = str(e)
        if attempt < retries:
            time.sleep(min(2**attempt, 8))
    return "failed", last_err


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download RFC plain-text files from rfc-editor.org")
    p.add_argument(
        "--rfcs",
        default="",
        help="Comma/space-separated numbers or ranges, e.g. 793,7680 or 8200-8210",
    )
    p.add_argument(
        "--from-file",
        type=Path,
        help="Text file: one RFC number or range per line (# comments allowed)",
    )
    p.add_argument(
        "-o",
        "--output",
        default="multicast_streaming_rfcs",
        help="Output directory (default: multicast_streaming_rfcs)",
    )
    p.add_argument("--force", action="store_true", help="Re-download even if file exists")
    p.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Concurrent downloads (default: 6; use 1 for sequential)",
    )
    p.add_argument("--retries", type=int, default=3, help="Attempts per RFC (default: 3)")
    p.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout seconds")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="HTTP User-Agent header")
    p.add_argument("--dry-run", action="store_true", help="Print planned downloads only")
    p.add_argument("-q", "--quiet", action="store_true", help="Less console output")
    args = p.parse_args(argv)

    numbers: list[int] = []
    if args.from_file:
        if not args.from_file.is_file():
            print(f"Error: --from-file not found: {args.from_file}", file=sys.stderr)
            return 2
        numbers = _load_rfc_file(args.from_file)
    if args.rfcs.strip():
        try:
            numbers = sorted(set(numbers) | set(_parse_rfc_list(args.rfcs)))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    if not numbers:
        numbers = list(DEFAULT_RFCS)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print(f"Downloading {len(numbers)} RFC(s) -> {out_dir.resolve()}\n")

    ok = skipped = failed = 0
    errors: list[tuple[int, str]] = []

    def _fetch_one(num: int) -> tuple[int, str, str | None]:
        status, err = fetch_rfc(
            num,
            out_dir / f"rfc{num}.txt",
            force=args.force,
            retries=max(1, args.retries),
            timeout=args.timeout,
            user_agent=args.user_agent,
            dry_run=args.dry_run,
            quiet=args.quiet,
        )
        return num, status, err

    def _report(num: int, status: str, err: str | None) -> None:
        nonlocal ok, skipped, failed
        if status == "ok":
            ok += 1
            if not args.quiet:
                print(f"RFC {num} ... " + ("ok" if not args.dry_run else "planned"))
        elif status == "skipped":
            skipped += 1
            if not args.quiet:
                print(f"RFC {num} ... skipped (already present)")
        else:
            failed += 1
            errors.append((num, err or "unknown"))
            if not args.quiet:
                print(f"RFC {num} ... FAILED ({err})")

    workers = max(1, min(int(args.workers), len(numbers)))
    if workers == 1 or args.dry_run:
        for num in numbers:
            _report(*_fetch_one(num))
    else:
        # Download concurrently: sequential fetches made wall-clock time the SUM
        # of every request (plus retry back-offs) instead of the slowest few.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_fetch_one, num) for num in numbers]
            for fut in as_completed(futures):
                _report(*fut.result())

    if not args.quiet:
        print(
            f"\nDone: {ok} ok, {skipped} skipped, {failed} failed "
            f"(total {len(numbers)} RFC(s))."
        )
    if errors and args.quiet:
        for num, msg in errors:
            print(f"RFC {num}: {msg}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
