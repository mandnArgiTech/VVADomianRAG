"""Mocked HTTP for Rally / Confluence; CSV helpers."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import ingest as ing


def test_fetch_rally_requires_requests(monkeypatch):
    monkeypatch.setattr(ing, "requests", None)
    with pytest.raises(RuntimeError, match="requests"):
        ing.fetch_rally_artifacts("p")


def test_fetch_rally_requires_key(monkeypatch):
    monkeypatch.delenv("RALLY_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="RALLY_API_KEY"):
        ing.fetch_rally_artifacts("p")


@patch("ingest.requests.get")
def test_fetch_rally_success(mock_get, monkeypatch):
    monkeypatch.setenv("RALLY_API_KEY", "secret")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "QueryResult": {
            "Results": [
                {"FormattedID": "DE1", "Description": "x" * 400, "Name": "N", "Severity": "2"},
            ],
            "TotalResultCount": 1,
        }
    }
    mock_get.return_value = resp
    out = ing.fetch_rally_artifacts("MyProject", page_size=200)
    assert len(out) == 1
    assert out[0]["FormattedID"] == "DE1"


@patch("ingest.requests.get")
def test_fetch_rally_pagination(mock_get, monkeypatch):
    monkeypatch.setenv("RALLY_API_KEY", "secret")
    r1 = MagicMock()
    r1.raise_for_status = MagicMock()
    r1.json.return_value = {
        "QueryResult": {
            "Results": [{"FormattedID": "DE1", "Description": "x" * 300}],
            "TotalResultCount": 2,
        }
    }
    r2 = MagicMock()
    r2.raise_for_status = MagicMock()
    r2.json.return_value = {
        "QueryResult": {
            "Results": [{"FormattedID": "DE2", "Description": "y" * 300}],
            "TotalResultCount": 2,
        }
    }
    mock_get.side_effect = [r1, r2]
    out = ing.fetch_rally_artifacts("P", page_size=1)
    assert len(out) == 2


def test_fetch_confluence_requires_env(monkeypatch):
    monkeypatch.delenv("CONFLUENCE_URL", raising=False)
    monkeypatch.delenv("CONFLUENCE_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="CONFLUENCE"):
        ing.fetch_confluence_pages("SPC")


@patch("ingest._fetch_confluence_pages_v2", return_value=None)
@patch("ingest.requests.get")
def test_fetch_confluence_v1(mock_get, _v2, monkeypatch):
    monkeypatch.setenv("CONFLUENCE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_TOKEN", "tok")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "results": [
            {
                "status": "current",
                "title": "Page",
                "id": "99",
                "metadata": {"labels": {"results": [{"name": "alpha"}]}},
                "version": {"when": "2024-01-01", "by": {"displayName": "U"}},
                "body": {"storage": {"value": "B" * 250}},
            }
        ],
        "_links": {},
    }
    mock_get.return_value = resp
    pages = ing.fetch_confluence_pages("SPC", "")
    assert len(pages) == 1
    assert len(pages[0]["body"]) >= 200


@patch("ingest.requests.get")
def test_fetch_confluence_v2_path(mock_get, monkeypatch):
    monkeypatch.setenv("CONFLUENCE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_TOKEN", "tok")

    space_resp = MagicMock()
    space_resp.status_code = 200
    space_resp.json.return_value = {"results": [{"id": "space-1"}]}

    page_resp = MagicMock()
    page_resp.status_code = 200
    page_resp.json.return_value = {
        "results": [
            {
                "status": "current",
                "title": "V2 Page",
                "id": "p1",
                "version": {"createdAt": "t"},
                "body": {"storage": {"value": "C" * 250}},
                "labels": {"results": [{"name": "doc"}]},
            }
        ],
        "_links": {},
    }
    mock_get.side_effect = [space_resp, page_resp]
    pages = ing._fetch_confluence_pages_v2(
        "https://example.atlassian.net",
        {"Authorization": "Bearer tok"},
        "SPC",
        "",
    )
    assert pages is not None
    assert len(pages) >= 1


@patch("ingest.requests.get")
def test_fetch_confluence_v2_space_error_returns_none(mock_get):
    mock_get.return_value.status_code = 500
    out = ing._fetch_confluence_pages_v2("https://x", {}, "SPC", "")
    assert out is None


def test_load_rally_rows_from_csv(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("FormattedID,Description,Severity\nDE1,Hello world text,2\n", encoding="utf-8")
    rows = ing.load_rally_rows_from_csv(p)
    assert rows[0]["FormattedID"] == "DE1"
