# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""
To run:

    $ cd os2mo-sdtool-plus
    $ poetry shell
    $ export MORA_BASE=http://localhost:5000
    $ export AUTH_SERVER=...
    $ export CLIENT_SECRET=...
    $ python -m sdtoolplus

"""
import click

from .app import App
from .tree_diff_executor import TreeDiffExecutor


@click.command()
def main() -> None:
    app: App = App()
    executor: TreeDiffExecutor = app.get_tree_diff_executor()
    for operation, mutation, result in executor.execute():
        print(operation, result)


if __name__ == "__main__":
    main()
