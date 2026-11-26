from types import SimpleNamespace
from nail_media.mediacrawler_runner import collect


def test_detail_adapter(tmp_path):
    project = tmp_path / "mc"
    project.mkdir()
    (project / "main.py").touch()
    task = {"platform":"douyin","project":str(project),"specified_ids":["123"],"limit":1}
    def runner(command, **kwargs):
        assert command[:3] == ["uv","run","main.py"]
        assert "--specified_id" in command
        assert "VIRTUAL_ENV" not in kwargs["env"]
        assert kwargs["cwd"] == project
        return SimpleNamespace(returncode=0)
    def importer(directory,root,limit,platform):
        assert limit == 1 and platform == "douyin"
        return {"posts":1,"errors":[]}
    assert collect(task,tmp_path,runner=runner,importer=importer)["status"] == "success"
    assert collect(task,tmp_path,runner=lambda *a,**k: SimpleNamespace(returncode=1))["status"] == "failed"
