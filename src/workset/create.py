import pathlib
import sys
from dataclasses import dataclass
from typing import List, Optional

from . import utils
from .config import Config, Repo


@dataclass
class CreateRequest:
    config: Config

    dest: pathlib.Path
    source: str
    repos: List[str]
    branch: Optional[str]
    message: Optional[str]
    suppress: bool


def create(r: CreateRequest) -> None:
    if "upgrade" in r.repos and not r.source.endswith("/master"):
        sys.exit("upgrade only works with the master branch")
    if "/" not in r.source:
        sys.exit(f"the source must include the remote name (got {r.source!r})")

    # all odoo stuff requires the community repo
    if "odoo" not in r.repos:
        r.repos.insert(0, "odoo")

    r.dest.mkdir(exist_ok=True)
    # mark the directory as a workset so it can be deleted (maybe) a soon as
    # the first clone is created
    (r.dest / ".workset").touch()

    modules: dict[str, Repo] = {}
    for repo in r.repos:
        conf = modules[repo] = r.config["repos"][repo]
        utils.checkout(
            dest=utils.checkout_path(r.dest, repo, conf),
            root=r.config.get("root"),
            name=repo,
            conf=conf,
            source=r.source,
            target=(r.branch or r.source.split("/", 1)[1])
            if r.suppress or not r.branch
            else "{}-{}".format(
                r.source.split("/", 1)[1],
                r.branch,
            ),
        )

    if r.message:
        (r.dest / "README.txt").write_text(r.message.rstrip() + "\n")

    # FIXME: retrieve from odoo minver
    (r.dest / ".python-version").write_text("3.12")

    dev = ["pytest", "pytest-timeout", "pytest-sugar", "pytest-xdist"]
    if "runbot" in r.repos:
        dev.extend(("setuptools", "sentry_sdk", "markdown", "cssselect"))
    else:
        dev.extend(
            (
                "pytest-odoo @ git+https://github.com/xmo-odoo/pytest-odoo",
                "pytest-runbot-autotags @ git+https://github.com/xmo-odoo/pytest-runbot-autotags",
            )
        )
    (r.dest / "pyproject.toml").write_text(f"""\
[build-system]
requires = ["odoo-deps-backend @ git+https://github.com/xmo-odoo/odoo-deps-backend"]
build-backend = "odoo_deps_backend"

[project]
name = "odoo"
version = "0.1.0"  # FIXME: make dynamic and fetch from odoo? Not sure that's useful.
requires-python = ">= 3.12"  # FIXME: retrieve from odoo minver
dynamic = ["dependencies"]

[dependency-groups]
dev = {dev!r}

[tool.setuptools]
# or the recursive setuptools call fails with "multiple top-level packages discovered
# in a flat-layout
py-modules = []
""")

    project = r.dest / ".idea"
    project.mkdir(parents=True, exist_ok=True)
    (project / "modules.xml").write_text(
        """\
<project version="4">
  <component name="ProjectModuleManager">
    <modules>
      <module fileurl="file://$PROJECT_DIR$/.idea/{name}.iml" filepath="$PROJECT_DIR$/.idea/{name}.iml" />
    </modules>
  </component>
</project>
""".format(name=r.dest.stem)
    )
    with (project / r.dest.stem).with_suffix(".iml").open("w", encoding="utf-8") as iml:
        iml.write("""\
<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$">
      <excludeFolder url="file://$MODULE_DIR$/.venv" />
""")
        for name, conf in modules.items():
            for mod in conf.get("pythonpath") or [name]:
                iml.write(
                    f'      <sourceFolder url="file://$MODULE_DIR$/{mod}" isTestSource="false"/>\n'
                )
            for exclude in conf.get("exclude", []):
                iml.write(
                    f'      <excludeFolder url="file://$MODULE_DIR$/{name}/{exclude}"/>\n'
                )
        iml.write(f"""\
    </content>
    <orderEntry type="jdk" jdkName="uv ({r.dest.stem})" jdkType="Python SDK" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
</module>
""")

    env: dict[str, str] = {}
    for name, mod in modules.items():
        pp = (
            str(r.dest.joinpath(p).resolve()) for p in (mod.get("pythonpath") or [name])
        )
        if env.get("PYTHONPATH"):
            env["PYTHONPATH"] += "".join(f":{p}" for p in pp)
        else:
            env["PYTHONPATH"] = ":".join(pp)
        env.update(mod.get("env") or {})

    (r.dest / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in env.items()),
        encoding="utf-8",
    )

    for name, mod in modules.items():
        for dest, source in (mod.get("links") or {}).items():
            link = (r.dest / dest).resolve()
            link.parent.mkdir(parents=True, exist_ok=True)
            target = (r.dest / name / source).resolve()
            link.symlink_to(
                target.relative_to(link.parent, walk_up=True),
                target_is_directory=target.is_dir(),
            )
