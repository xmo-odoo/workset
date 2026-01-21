import pathlib
import sys
import tomllib
from argparse import ArgumentParser

from .create import create
from .add import add
from .delete import delete


CONF = pathlib.Path("~/.config/workset/config.toml")


def main() -> None:
    if (p := CONF.expanduser().resolve()).is_file():
        print("conf:", CONF, file=sys.stderr)
        with p.open("rb") as f:
            config = tomllib.load(f)
    else:
        config = {}

    p = ArgumentParser()
    p.set_defaults(func=None, config=config)

    sp = p.add_subparsers()

    create_parser = sp.add_parser("create", help="create a new workset")
    create_parser.set_defaults(func=create)
    create_parser.add_argument(
        "-r",
        "--repos",
        action="extend",
        nargs="*",
        choices=config["repos"].keys(),
        default=[],
    )
    create_parser.add_argument(
        "-b",
        "--branch",
        help="working branch (automatically includes source as prefix)",
    )
    create_parser.add_argument(
        "-m", "--message", help="Reminder message for the workset"
    )
    create_parser.add_argument(
        "-s",
        "--suppress",
        action="store_true",
        default=False,
        help="Suppress automatic prepending of source branch",
    )
    create_parser.add_argument("source", help="source branch")
    create_parser.add_argument("dest", type=pathlib.Path, help="destination directory")

    add_parser = sp.add_parser("add", help="add a repository to a workset")
    add_parser.set_defaults(func=add)
    add_parser.add_argument("-s", "--source", help="source branch")
    add_parser.add_argument(
        "-w",
        "--workset",
        type=pathlib.Path,
        default=".",
        help="workset to update (default: current directory)",
    )
    add_parser.add_argument(
        "repos", action="extend", nargs="*", choices=config["repos"].keys(), default=[]
    )

    delete_parser = sp.add_parser("delete", help="delete a workset")
    delete_parser.set_defaults(func=delete)
    delete_parser.add_argument(
        "-b", "--branch", action="store_true", help="Delete checked out branch"
    )
    delete_parser.add_argument(
        "-f", "--force", action="store_true", help="Delete worktree even if dirty"
    )
    delete_parser.add_argument("workset", type=pathlib.Path)

    help_parser = sp.add_parser("help")
    help_parser.add_argument("subcommand", nargs="?", choices=sp.choices.keys())
    help_parser.set_defaults(
        func=lambda args: (
            sp.choices[args.subcommand] if args.subcommand else p
        ).print_help()
    )
    args = p.parse_args()
    if not args.func:
        p.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
