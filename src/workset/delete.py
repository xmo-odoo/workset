import pathlib
import shutil
import sys
from dataclasses import dataclass
from typing import TypedDict
from subprocess import run, DEVNULL

from . import utils
from .config import Config


@dataclass
class DeleteRequest:
    config: Config

    workset: pathlib.Path
    branch: bool
    force: bool


class Info(TypedDict):
    worktree: pathlib.Path
    repo: pathlib.Path
    branch: str


def delete(r: DeleteRequest) -> None:
    if not (r.workset / ".workset").is_file():
        sys.exit(f"{r.workset} does not seem to be a workset")

    worktrees: dict[str, Info] = {}
    for repo in r.workset.iterdir():
        if not repo.is_dir() or repo.stem.startswith("."):
            continue
        checkout_conf = r.config["repos"].get(repo.stem)
        if (
            checkout_conf is None
        ):  # TODO: should repos default to a trivial modules type?
            print(f"Unknown checkout {repo.stem!r}, ignoring...", file=sys.stderr)
            continue

        checkout = utils.checkout_path(
            r.workset, repo.stem, r.config["repos"].get(repo.stem)
        )
        if not checkout.is_dir():
            sys.exit(f"Expected git checkout for {repo.stem} at {checkout}")

        repo = (
            checkout
            / run(
                ["git", "-C", checkout, "rev-parse", "--git-common-dir"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )

        if not r.force:
            if run(["git", "-C", checkout, "diff", "--quiet"]).returncode:
                sys.exit(
                    f"{checkout} is dirty, ensure all changes are committed or use `-f`"
                )

        br = run(
            ["git", "-C", checkout, "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )

        worktrees[repo.stem] = {
            "worktree": checkout,
            "repo": repo,
            "branch": br.stdout.strip(),
        }

    branches = set()
    if r.branch:
        branches = {r["branch"] for r in worktrees.values()}
        if len(branches) > 1:
            sys.exit(
                f"Expected all worktrees to be on the same branch, found {', '.join(branches)}"
            )

    for attrs in worktrees.values():
        # if it's a clone (repo is inside the working copy)
        if attrs["repo"].is_relative_to(attrs["worktree"]):
            # move working copy off of branch (if any) in case we need to delete the branch
            run(["git", "-C", attrs["worktree"], "switch", "-d"])
        else:
            # else remove the worktree
            run(["git", "-C", attrs["worktree"], "worktree", "remove", "--force", "."])

    if branches:
        [b] = branches
        answer = input(f"deleting branch {b} in {len(worktrees)} repository/ies [yN]: ")
        if answer == "y":
            for w in worktrees.values():
                run(
                    ["git", "-C", w["repo"], "branch", "-D", b],
                    check=True,
                    stdout=DEVNULL,
                )

    shutil.rmtree(r.workset.resolve())
