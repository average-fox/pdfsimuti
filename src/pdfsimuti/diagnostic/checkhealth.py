import importlib.util

from rich import print
from rich.pretty import Pretty
from rich.panel import Panel

import typer
from typing_extensions import Annotated

packages_list = ['pymupdf', 'magic', 'ghostscript']

def display_render_msg(package_name):
    return Panel(Pretty(importlib.util.find_spec(package_name) is not None))


def verbose_level_1():
    for package in packages_list:
        print(package)
        print(display_render_msg(package))
    


# Option 1: Create an alternate screen using Python Rich library and display the health. Press 'q' to exit
# Option 2: Just print it on terminal.
# EXTRA: Verbose levels. Level 1: True/False, Level 2: Origin, Level 3: Everything

## NOTE: You should do Option 1 because it gives a vibe like Neovim.


def checkhealth(verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, max=3, help="Verbose level")] = 1):
    match verbose:
        case 1: verbose_level_1()
        case 2: print("Not implemented")
        case 3: print("Not implemented")
    