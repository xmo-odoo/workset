# Worksets

Build work-set of Odoo repos, and setup a PyCharm project.

## Configuration

The configuration file is composed of:

- `root` (optional), provides the root directory for repositories in order to  
  create worksets, `{root}/{repo.name}` will be the base for creating working 
  copies.
- `repos` is a table of name: configuration, the name is used for looking up
  in `root` as well as creating the working copy
- `repos.{name}.method`, the method for creating working copies, if a `root`
  is provided it defaults to `worktree`, otherwise it defaults to `clone`
  (which as its name indicates creates a clone, either of a reference
  repository in `root`, or of the specified url)
- `repos.{name}.type` the repository type, one of:
  - `root`, if the working copy is to be checked out directly at `{name}/` and
    a `PYTHONPATH` root
  - `modules`, if the working copy is a directory of modules to check
    out at `{name}/odoo/addons/`
  - TODO `submodules`, if the working copy is a directory of `modules` directories
- TODO `repos.{name}.path` a custom checkout path
- `repos.{name}.links` a table of paths from the project toplevel to
  inside the working copy, can be used to bring configuration files up, or
  to create ancillary `PYTHONPATH` entries
- `pythonpath` an array of `PYTHONPATH` entries (relative to the
  project root), defaults to `["{name}"]`
- `repos.{name}.exclude` an array of paths relative to the project root to 
  `excludeFolder` from the pycharm project
- `repos.{name}.env` a table of additional entries for the env file
- TODO `repos.{name}.url` clone reference if not using `root`

## Project Layout
--------------

Projects are setup using namespace packages (PEP 420) rather than
addons paths, as that makes it easier for tooling to find its way.

Community addons are currently not setup for that.

The primary drawback is the git interactions are a bit shit, it might
be better to use symlinks and have the IDE and git views separate.

PyCharm Layout
--------------

PyCharm is currently setup using a single project with various
directories (e.g. odoo, enterprise, runbot). This makes for a very
simple setup, however I'm not sure it's compatible with shared
indexes, so if I setup local shared indexes (generated for the odoo
repos, mainly community & enterprise) and it doesn't work I might have
to switch to a multi-modules system (where each checkout is its own
idea project with an iml, and then there's a modules.xml which links
to all the imls, note that having a per-repo modules.xml might not be
necessary, to check)

Pregenerating the index would be quite useful, as currently indexing
for a project on master using odoo & enterprise takes around 80
seconds, apparently the git log indexing doesn't start up immediately
so that's some time saved.
