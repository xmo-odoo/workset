from __future__ import annotations

from typing import Optional, TypedDict, Literal, Required


class Config(TypedDict, total=False):
    root: str
    repos: dict[str, Repo]


class Repo(TypedDict, total=False):
    type: Required[Literal["root", "modules", "submodules"]]
    links: dict[str, str]
    pythonpath: list[str]
    env: dict[str, str]
    exclude: list[str]
    # TODO: implement these?
    method: Literal["worktree", "clone"]
    url: Optional[str]
    path: Optional[str]
