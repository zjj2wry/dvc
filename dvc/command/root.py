import os

import dvc.logger as logger
from dvc.command.base import CmdBase


class CmdRoot(CmdBase):
    def run_cmd(self):
        return self.run()

    def run(self):
        logger.info(os.path.relpath(self.project.root_dir))
        return 0


def add_parser(subparsers, parent_parser):
    ROOT_HELP = "Relative path to project's directory."
    root_parser = subparsers.add_parser(
        'root',
        parents=[parent_parser],
        description=ROOT_HELP,
        help=ROOT_HELP)
    root_parser.set_defaults(func=CmdRoot)
