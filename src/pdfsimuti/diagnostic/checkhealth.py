import sys

import importlib.util
from importlib.metadata import version

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import typer
from typing_extensions import Annotated

console = Console()

packages_dict = {
    'pymupdf' : [
        importlib.util.find_spec('pymupdf'),
        version('pymupdf'),
        """
Used as the main package for merging the files. Also have features to provide simple compressions.
        """
        
    ],
    'magic' : [
        importlib.util.find_spec('magic'),
        version('python-magic-bin' if sys.platform == "win32" else 'python-magic'),
        """
Used for checking if the file is actually the file format it claims to be. It checks for their mimecheck type.
Without this, you cannot do something like the following~
[code]pdfsimuti merge --no-validate FILE1.pdf FILE2.pdf[/code] 
        """
    ]
}


def verbose_level_1():
    panel_content = "\n".join(f"{key}: {'[green]Installed[/green]' if value else '[red]Not Installed[/red]'}" for key, value in packages_dict.items())
    console.print(Panel(panel_content, title="pdfSimUti checkhealth"))
    
    
def verbose_level_2():
    table = Table(show_lines=True, show_edge=False, expand=True)
    table.add_column("Package Name", justify="center", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Location", justify="center")
    
    for package, item in packages_dict.items():
        table.add_row(package, "[green]Installed[/green]" if item[0] else "[red]Not Found[/red]", str("/n".join(item[0].submodule_search_locations)) if item[0] is not None else "[red]Not found[/red]")
    
    console.print(Panel(table, title="pdfSimUti checkhealth"))


def verbose_level_3():
    for package, item in packages_dict.items():
        console.rule(f"'{package}' description")
        console.print(f"""
[u]Package name[/u]: {package}
[u]Package version[/u]: {item[1]}
[u]Package ModuleSpec[/u]: {item[0]}

[u]Description[/u]: {item[2]}
""")

# Option 1: Create an alternate screen using Python Rich library and display the health. Press 'q' to exit
# Option 2: Just print it on terminal.
# EXTRA: Verbose levels. Level 1: True/False, Level 2: Origin, Level 3: Everything
# EXTRA: Do something like 'exists at ....location'

## NOTE: You should do Option 1 because it gives a vibe like Neovim.

def checkhealth(verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, max=3, help="Verbose level")] = 1):
    
    match verbose:
        case 1: verbose_level_1()
        case 2: verbose_level_2()
        case 3: verbose_level_3()
    