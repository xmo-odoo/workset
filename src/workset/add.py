import os
import pathlib
import sys
from dataclasses import dataclass
from subprocess import run, PIPE
from xml.etree import ElementTree as etree

from workset.config import Config


@dataclass
class AddRequest:
    config: Config

    workset: pathlib.Path
    repos: list[str]
    source: str | None


def add(req: AddRequest) -> None:
    if not (req.workset / ".workset").is_file():
        sys.exit(f"{req.workset} is not a workset")

    out = run(
        ["git", "-C", req.workset / "odoo", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
        stdout=PIPE,
        encoding="utf-8",
    )
    target = out.stdout.strip()

    mod = etree.parse(req.workset / ".idea/modules.xml")
    imlpath = (
        mod.find(".//module")
        .attrib["filepath"]
        .replace("$PROJECT_DIR$", os.fspath(req.workset))
    )
    iml = etree.parse(imlpath)

    options = iml.find(".//component[@name='PyNamespacePackagesService']/option/list")
    existing = {
        "odoo",
        "community",
    }  # assume these two are always present in a valid workset
    existing.update(
        opt.attrib["value"].removeprefix("$MODULE_DIR$/")
        for opt in options.iterfind("./option")
    )
    new_repos = [r for r in req.repos if r not in existing]

    if req.source:
        if "/" not in req.source:
            sys.exit(f"the source must include the remote name (got {req.source!r})")
        source = req.source
    else:
        # TODO: maybe check if `target` is an existing branch on the target first?
        source = (
            "origin/" + target[:9] if target.startswith("saas") else "origin/master"
        )
        for repo in new_repos:
            if run(
                [
                    "git",
                    "--git-dir",
                    repos[repo],
                    "show-ref",
                    "--quiet",
                    f"refs/remotes/{source}",
                ]
            ).returncode:
                sys.exit(
                    f"inferred source branch {source!r} not found in {repos[repo]!r}"
                )

    # TODO: is it possible for other modules than `odoo` to have a root config?
    #       ignore for now, assume it all goes elsewhere
    modules: dict[str, Repo] = {}
    for repo in new_repos:
        dest: Repo
        dest = modules[repo] = repo_layouts[repo](req.workset, repo)
        dest.checkout(
            source=source,
            target=target,
        )

    for name, conf in modules.items():
        if n := conf.namespace():
            if len(options):
                end = options[-1].tail
                options[-1].tail = options[-2].tail
                options.append(etree.fromstring(n))
                options[-1].tail = end
            else:
                options.append(etree.fromstring(n))
    iml.write(imlpath)

    # TODO: quoting, interpolation, comments, ...
    env = {
        entry.split("=", 1)
        for entry in (r.workset / ".env")
        .read_text(encoding="utf-8")
        .splitlines(keepends=False)
    }
    for mod in modules.values():
        mod.postprocess(env)
    (r.workset / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in env.items()),
        encoding="utf-8",
    )
