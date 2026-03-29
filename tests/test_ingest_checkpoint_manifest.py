"""Checkpoint, migration, manifest, ingestion config."""
from __future__ import annotations

import json
from pathlib import Path

import ingest as ing


def test_migrate_old_checkpoint(tmp_path):
    old = tmp_path / "ingestion_checkpoint.json"
    new = tmp_path / "ingest_checkpoint.json"
    old.write_text('{"a": "1", "b": "2"}', encoding="utf-8")
    ing.migrate_old_checkpoint(tmp_path, "coll")
    assert new.exists()
    data = json.loads(new.read_text(encoding="utf-8"))
    assert "coll::checkpoint" in data


def test_migrate_skips_if_new_exists(tmp_path):
    old = tmp_path / "ingestion_checkpoint.json"
    new = tmp_path / "ingest_checkpoint.json"
    old.write_text("{}", encoding="utf-8")
    new.write_text("{}", encoding="utf-8")
    ing.migrate_old_checkpoint(tmp_path, "coll")
    assert new.read_text() == "{}"


def test_load_save_checkpoint_roundtrip(tmp_path):
    assert ing.load_checkpoint(tmp_path) == {}
    ing.save_checkpoint(tmp_path, {"k": "v"})
    assert ing.load_checkpoint(tmp_path) == {"k": "v"}


def test_load_checkpoint_bad_json(tmp_path):
    p = tmp_path / "ingest_checkpoint.json"
    p.write_text("not json", encoding="utf-8")
    assert ing.load_checkpoint(tmp_path) == {}


def test_write_ingestion_config(tmp_path):
    ing.write_ingestion_config(tmp_path, "mymodel")
    cfg = json.loads((tmp_path / "ingestion_config.json").read_text(encoding="utf-8"))
    assert cfg["embedding_model"] == "mymodel"


def test_append_manifest(tmp_path):
    ing.append_manifest(tmp_path, {"ingestion_id": "1", "mode": "domain"})
    lines = (tmp_path / "ingestion_history.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    ing.append_manifest(tmp_path, {"ingestion_id": "2"})
    lines2 = (tmp_path / "ingestion_history.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines2) == 2


def test_update_repos_manifest(tmp_path):
    ing.update_repos_manifest(tmp_path, "nms_code", {"repo1": 5})
    data = json.loads((tmp_path / "repos_manifest.json").read_text(encoding="utf-8"))
    assert data["by_collection"]["nms_code"]["repo1"] == 5


def test_update_repos_manifest_merge(tmp_path):
    path = tmp_path / "repos_manifest.json"
    path.write_text('{"by_collection": {"x": {}}}', encoding="utf-8")
    ing.update_repos_manifest(tmp_path, "y", {"z": 1})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "y" in data["by_collection"]
