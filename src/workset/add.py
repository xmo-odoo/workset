import os
import pathlib
import sys
from dataclasses import dataclass
from subprocess import run, PIPE
from xml.etree import ElementTree as etree

from workset import utils
from workset.config import Config, Repo


@dataclass
class AddRequest:
    config: Config

    workset: pathlib.Path
    repos: list[str]
    source: str | None


def add(req: AddRequest) -> None:
    if not (req.workset / ".workset").is_file():
        sys.exit(f"{req.workset} is not a workset")

    mod = etree.parse(req.workset / ".idea/modules.xml")
    imlpath = (
        mod.find(".//module")
        .attrib["filepath"]
        .replace("$PROJECT_DIR$", os.fspath(req.workset))
    )
    iml = etree.parse(imlpath)

    content = iml.find(".//content")
    existing = {
        source.attrib['url'].removeprefix("file://$MODULE_DIR$/")
        for source in content.iterfind('.//sourceFolder')
    }
    new_repos = [r for r in req.repos if r not in existing]

    out = run(
        ["git", "-C", req.workset / "odoo", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
        stdout=PIPE,
        encoding="utf-8",
    )
    target = out.stdout.strip()
    if target == 'HEAD':
        target = None
    if req.source:
        if "/" not in req.source:
            sys.exit(f"the source must include the remote name (got {req.source!r})")
        source = req.source
        if target is None:
            _,  target = source.split("/", 1)
    elif target:
        source = (
            "origin/" + target[:9] if target.startswith("saas") else "origin/master"
        )
        for repo in new_repos:
            origin = utils.get_origin(req.config['root'], repo)
            if run(
                    [
                        "git",
                        "--git-dir",
                        origin,
                        "show-ref",
                        "--quiet",
                        f"refs/remotes/{source}",
                    ]
            ).returncode:
                sys.exit(
                    f"inferred source branch {source!r} not found in {origin!r}"
                )
    else:
        sys.exit("Unable to infer target branch from odoo/, provide source")

    modules: dict[str, Repo] = {}
    for repo in new_repos:
        conf = modules[repo] = req.config["repos"][repo]
        utils.checkout(
            dest=utils.checkout_path(req.workset, repo, conf),
            root=req.config.get("root"),
            name=repo,
            conf=conf,
            source=source,
            target=target,
        )

    for name, conf in modules.items():
        for mod in conf.get("pythonpath") or [name]:
            etree.SubElement(
                content,
                "sourceFolder",
                url=f"file://$MODULE_DIR$/{mod}",
                isTestSource="false",
            )
        for exclude in conf.get("exclude", []):
            etree.SubElement(
                content,
                "excludeFolder",
                url=f"file://$MODULE_DIR$/{name}/{exclude}",
            )
    iml.write(imlpath)

    # TODO: quoting, interpolation, comments, ...
    env = dict(
        entry.split("=", 1)
        for entry in (req.workset / ".env")
        .read_text(encoding="utf-8")
        .splitlines(keepends=False)
    )
    for name, mod in modules.items():
        env["PYTHONPATH"] += "".join(
            f":{req.workset.joinpath(p).resolve()}"
            for p in (mod.get("pythonpath") or [name])
        )
        env.update(mod.get("env") or {})

    (req.workset / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in env.items()),
        encoding="utf-8",
    )

    for name, mod in modules.items():
        for dest, source in (mod.get("links") or {}).items():
            link = (req.workset / dest).resolve()
            link.parent.mkdir(parents=True, exist_ok=True)
            target = (req.workset / name / source).resolve()
            link.symlink_to(
                target.relative_to(link.parent, walk_up=True),
                target_is_directory=target.is_dir(),
            )
