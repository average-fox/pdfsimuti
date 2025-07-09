import importlib.util

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import typer
from typing_extensions import Annotated

console = Console()
packages_dict = {'pymupdf': None, 'magic': None, 'ghostscript': None} # key: package, value: None (not checked yet)

def do_the_packages_exist(packages_dict:dict):
    for keys, value in packages_dict.items():
        packages_dict[keys] = importlib.util.find_spec(keys)


def verbose_level_1():
    panel_content = "\n".join(f"{key}: {'[green]Installed[/green]' if value else '[red]Not Installed[/red]'}" for key, value in packages_dict.items())
    console.print(Panel(panel_content, title="pdfSimUti checkhealth"))
    
def verbose_level_2():
    table = Table(show_lines=True, show_edge=False, expand=True)
    table.add_column("Package Name", justify="center", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Location", justify="center")
    
    for name, origin in packages_dict.items():
        table.add_row(name, "[green]Installed[/green]" if origin else "[red]Not installed[/red]", str("/n".join(origin.submodule_search_locations)) if origin is not None else "[red]Not found[/red]")
    
    console.print(Panel(table, title="pdfSimUti checkhealth"))

# Option 1: Create an alternate screen using Python Rich library and display the health. Press 'q' to exit
# Option 2: Just print it on terminal.
# EXTRA: Verbose levels. Level 1: True/False, Level 2: Origin, Level 3: Everything
# EXTRA: Do something like 'exists at ....location'

## NOTE: You should do Option 1 because it gives a vibe like Neovim.

def checkhealth(verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, max=3, help="Verbose level")] = 1):
    
    do_the_packages_exist(packages_dict)
    
    match verbose:
        case 1: verbose_level_1()
        case 2: verbose_level_2()
        case 3: print("Not implemented")