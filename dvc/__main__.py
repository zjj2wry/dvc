"""Main entry point for dvc command line tool."""

import sys

from dvc.main import main

if __name__ == '__main__':
    main(sys.argv[1:])
