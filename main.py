"""Elanor - Minimalist static site generator.

This module provides the command-line entrypoint and re-exports all public
components from the `elanor` package for backwards compatibility.
"""

from elanor import *
from elanor.cli import main

if __name__ == '__main__':
    main()
