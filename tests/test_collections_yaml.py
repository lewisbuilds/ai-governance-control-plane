from pathlib import Path

import yaml


def test_collection_file_parses_and_has_top_level_mapping():
    # Resolve path relative to repo root (parent of tests/)
    repo_root = Path(__file__).parent.parent
    p = repo_root / "collections" / "ai-governance-control-plane.collection.yml"
    assert p.exists(), f"Collection file is missing at {p}"
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Collection YAML must be a mapping"
    # Soft expectations to reduce brittleness across schema changes
    for key in ("name", "description"):
        assert key in data, f"Expected top-level key '{key}' in collection"
