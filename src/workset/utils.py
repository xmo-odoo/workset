from pathlib import Path
from subprocess import run
from typing import Optional

from workset.config import Repo


def checkout_path(
    root: Path,
    name: str,
    config: Repo,
) -> Path:
    if path := config.get("path"):
        return root / path
    if config["type"] == "modules":
        return root / name / "odoo/addons"
    if config["type"] == "root":
        return root / name
    raise ValueError(f"Unknown type {config['type']!r}")


def checkout(
    dest: Path,
    root: Optional[str],
    name: str,
    conf: Repo,
    source: str,
    target: str,
) -> None:
    # TODO: conf.method
    if clone_url := conf.get("url"):
        assert source.startswith("origin/"), (
            "sources other than origin not supported for clones"
        )
        run(["git", "clone", clone_url, "-n", dest], check=True)
        if source.endswith("/" + target):
            run(["git", "-C", dest, "switch", "-d", source], check=True)
        else:
            run(
                ["git", "-C", dest, "switch", "-c", target, "--no-track", source],
                check=True,
            )
    else:
        assert root, (
            f"without URL, repository {name!r} needs a root repository directory"
        )
        origin = get_origin(root, name)
        if source.endswith("/" + target):
            run(
                ["git", "--git-dir", origin, "worktree", "add", dest, source],
                check=True,
            )
        else:
            run(
                [
                    "git",
                    "--git-dir",
                    origin,
                    "worktree",
                    "add",
                    "-b",
                    target,
                    "--no-track",
                    dest,
                    source,
                ],
                check=True,
            )


def get_origin(root: str, name: str) -> Path:
    return Path(root).expanduser().resolve().joinpath(name).with_suffix(".git")
