import sys
import textwrap # for not making this a cursed code for outputs.

import importlib.util
from importlib.metadata import version

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import typer
from typing_extensions import Annotated

console = Console(highlight=True)

packages_dict = {
    # 'PACKAGE_NAME' : [version, origin, search location,  installed?, description]
    'pymupdf' : [None,None,None,False,
        """
        Used as the main package for merging the files. Also have features to provide simple compressions.
        """],
    
    
    'magic' : [None, None,None,False,
        """
        Used for checking if the file is actually the file format it claims to be. It checks for their mimecheck type.
        Without this, you cannot do something like the following~
        [code]pdfsimuti merge --no-mimecheck FILE1.pdf FILE2.pdf[/code]
        """]
}

def update_packages_dict():
    for package, item in packages_dict.items():
        
        spec = importlib.util.find_spec(package)
        if package == "magic" and spec != None: item[0] = version('python-magic-bin' if sys.platform == "win32" else 'python-magic')
        # whoever decided magic should have different package names should be hanged.
        
        if spec:
            if not item[0]: item[0] = version(package)
            item[1] = spec.origin
            item[2] = "".join(spec.submodule_search_locations)
            item[3] = True


def verbose_level_1():
    panel_content = "\n".join(f"{key}: {'[green]Installed[/green]' if value[1] else '[red]Not Installed[/red]'}" for key, value in packages_dict.items())
    console.print(Panel(panel_content, title="pdfSimUti checkhealth"))
    
    
def verbose_level_2():
    table = Table(show_lines=True, show_edge=False, expand=True)
    table.add_column("Package Name", justify="center", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Location", justify="center")
    
    for package, item in packages_dict.items():
        table.add_row(package, "[green]Installed[/green]" if item[3] else "[red]Not Found[/red]", item[2] if item[2] else "[red]Not Found[/red]")
    console.print(Panel(table, title="[#00ffef]pdfSimUti checkhealth[/#00ffef]", padding=1))


def verbose_level_3():
    for package, item in packages_dict.items():
        console.print(Panel(textwrap.dedent(f"""
        [u]Package name[/u]: [#00ffef]{package}[/#00ffef]
        [u]Package version[/u]: {f"[bold green]{item[0]}[/bold green]" if item[0] else "[red]Not found[/red]"}
        [u]Package Origin[/u]: {f"[#a2a2d0]{item[1]}[/#a2a2d0]" if item[1] else "[red]Not found[/red]"}
        [u]Package Search[/u]: {f"[#ff9f00]{item[2]}[/#ff9f00]" if item[2] else "[red]Not found[/red]"}

        [u]Description[/u]: {item[4]}
        """).strip()),markup=True)


def checkhealth(verbose: Annotated[int, typer.Option("--verbose", "-v", "-V", count=True, max=3, help="Verbose level")] = 1):
    
    update_packages_dict() # wrote this otherwise the code would have been ugly
    match verbose:
        case 1: verbose_level_1()
        case 2: verbose_level_2()
        case 3: verbose_level_3()