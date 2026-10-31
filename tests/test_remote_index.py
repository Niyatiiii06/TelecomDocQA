"""Step 8: downloading the prebuilt index from Hugging Face."""

import pytest

from telecomdocqa import config, remote_index


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "CHUNKS_PATH", tmp_path / "processed" / "chunks.jsonl")
    monkeypatch.setattr(config, "INDEX_INFO_PATH", tmp_path / "index" / "index_info.json")
    monkeypatch.setattr(config, "CHROMA_DIR", tmp_path / "index" / "chroma")
    return tmp_path


def fake_download(**kwargs):
    """Pretend to download: create the files a real download would."""
    root = config.DATA_DIR
    (root / "processed").mkdir(parents=True)
    (root / "processed" / "chunks.jsonl").write_text("{}\n")
    (root / "index" / "chroma").mkdir(parents=True)
    (root / "index" / "index_info.json").write_text("{}")
    fake_download.calls.append(kwargs)


def test_downloads_only_when_missing(data_dir, monkeypatch):
    import huggingface_hub

    fake_download.calls = []
    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_download)
    assert remote_index.ensure_index("someone/index") is True
    assert fake_download.calls[0]["repo_type"] == "dataset"
    assert fake_download.calls[0]["allow_patterns"] == ["processed/*", "index/*"]
    assert remote_index.ensure_index("someone/index") is False   # already there: no second download
    assert len(fake_download.calls) == 1


def test_incomplete_download_is_an_error(data_dir, monkeypatch):
    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda **kwargs: None)
    with pytest.raises(RuntimeError):
        remote_index.ensure_index("someone/empty")
