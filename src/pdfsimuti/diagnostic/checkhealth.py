import typer
import sys
import subprocess # capture output
from subprocess import CompletedProcess

import importlib.util # getting package ModuleSpec
from importlib.metadata import version # for checking packages versions

from typing import TypedDict

from rich import prompt, tree, padding, box
from rich.panel import Panel
from rich.console import Console, Group, RenderableType
from pdfsimuti.main import __version__

from pdfsimuti.utils import get_gs_name
gs_name = get_gs_name()

pdfsimuti_package_stat = None
app = typer.Typer()
console = Console()

class packagesInfoTyped(TypedDict):
    packageName: str
    version: str
    searchLoc: str | None
    installed: bool


packages_dict:dict[str, packagesInfoTyped] = {
    'pymupdf' : {
        "packageName": "pymupdf",
        "version": "[red]Not found[/red]", 
        "searchLoc": "[red]Not found[/red]", 
        "installed": False
        },
    
    "ghostscript" : {
        "packageName": get_gs_name(),
        "version": "[red]Not found[/red]",
        "searchLoc": "[red]Not found[/red]",
        "installed": False
        },
    'typer' : {
            "packageName": "typer",
            "version": "[red]Not found[/red]", 
            "searchLoc": "[red]Not found[/red]", 
            "installed": False
        },
    'rich' : {
            "packageName": "rich",
            "version": "[red]Not found[/red]", 
            "searchLoc": "[red]Not found[/red]", 
            "installed": False
        },
    'click' : {
            "packageName": "click",
            "version": "[red]Not found[/red]", 
            "searchLoc": "[red]Not found[/red]", 
            "installed": False
    },
      
}


def check_gs_installation(gs_name:str) -> CompletedProcess[str] | None:
    try:
        return subprocess.run([gs_name, '--version'], capture_output=True, text=True)
    except FileNotFoundError:
        return None


def get_packages_status(*args:str):
    """
    Get package's moduleSpec, installed locations and other details.
    """

    for package in args:
        match package:
            case 'ghostscript': 
                if (result := check_gs_installation(gs_name=gs_name)):
                    import shutil
                    bin_loc = shutil.which(gs_name) # get location of the package
                    packages_dict["ghostscript"]["version"] = result.stdout.rstrip() # rstrip gets rid of the /n that comes from the capture_output
                    packages_dict["ghostscript"]["searchLoc"] = bin_loc
                    packages_dict["ghostscript"]["installed"] = True
            case _:
                if (spec := importlib.util.find_spec(package)):
                    packages_dict[package]["version"] = version(packages_dict[package]["packageName"])
                    packages_dict[package]["searchLoc"] = (spec.submodule_search_locations or [""])[0]
                    packages_dict[package]["installed"] = True


def return_checkhealth_renderable() -> RenderableType:
    """
    Return renderable group as display output for checkhealth.
    """
    spec = importlib.util.find_spec("pdfsimuti")
    pdfsimuti_package_stat: str | None = (
        spec.submodule_search_locations[0]
        if spec and spec.submodule_search_locations
        else "")
    
    package_tree = tree.Tree(Panel("Package Status", expand=False), guide_style="bold bright_blue")

    for package in packages_dict.items():
        pac = package_tree.add(Panel(package[0], expand=False))
        pac.add(f"[u][b]Status:[/b][/u] " + "[green]Installed[/green]" if package[1]["installed"] else "[red]Not Installed[/red]")
        pac.add("[u][b]Version:[/b][/u] " + package[1]["version"])
        pac.add("[u][b]Source:[/b][/u] " + f"[i]{package[1]["searchLoc"]}[/i]") 

    main_tree = tree.Tree(Panel(f"pdfSimuti v{__version__} checkhealth\n[i]a python typer + rich simple pdf utility tool.[/i]", expand=False, box=box.DOUBLE), guide_style="underline2")
    main_tree.add(console.render_str("[u]Installed source[/u]: " + f"{pdfsimuti_package_stat}"))
    main_tree.add(package_tree)

    return Group(
        main_tree,
        console.render_str("\n\n[green]Made by average-fox[/green]\n[i]Send suggestions, bugs or issues etc. on GitHub[/i]")
    )


@app.command(
    help="""
    Show health of the pdfSimUti packages.
    """
    )
def checkhealth():
    """
    Diagonstic App Command for pdfsimuti checkhealth
    """

    # update package status
    get_packages_status('pymupdf', 'ghostscript', 'rich', 'typer', 'click')

    with console.screen():
        console.print(padding.Padding(return_checkhealth_renderable(), (1,1)))
        prompt.Prompt.ask("\nEnter any key to continue")