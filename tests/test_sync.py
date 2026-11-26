import pytest
from nail_media.sync import sync

def test_requires_confirmation(tmp_path):
    with pytest.raises(PermissionError):
        sync(tmp_path/"catalog.sqlite3",tmp_path)

def test_rejects_unexpected_remote(tmp_path,monkeypatch):
    calls=[]
    def git(args,**kwargs):
        calls.append(args)
        return "https://example.org/other.git"
    monkeypatch.setattr("nail_media.sync.subprocess.check_output",git)
    with pytest.raises(ValueError,match="Unexpected archive repository"):
        sync(tmp_path/"catalog.sqlite3",tmp_path,confirmed=True)
    assert len(calls)==1
