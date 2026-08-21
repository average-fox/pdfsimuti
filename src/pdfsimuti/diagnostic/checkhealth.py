import sys
import shutil # used for getting ghostscriptapplication PATH variables
import subprocess # capture output

import importlib.util # getting package ModuleSpec
from importlib.metadata import version # for checking packages versions

from typing import TypedDict

pdfsimuti_package_stat = None

class packageInfo(TypedDict):
    version: str
    searchLoc: str
    installed: str

packages_dict:dict[str, packageInfo] = {
    'pymupdf' : {
        "version": "[red]Not found[/red]", 
        "searchLoc": "[red]Not found[/red]", 
        "installed": "[red]Not installed[/red]"
        },
    
    'magic' : {
        "version": "[red]Not found[/red]", 
        "searchLoc": "[red]Not found[/red]", 
        "installed": "[red]Not installed[/red]"
        },
    
    "ghostscript" : {
        "version": "[red]Not found[/red]",
        "searchLoc": "[red]Not found[/red]",
        "installed": "[red]Not installed[/red]"
        }    
}


def update_packages_dict(*args):
    """
    Update 'packages_dict' of their moduleSpec, installed location and other info.
    """

    # Note: magic in importlib.util.find_spec is not a valid name for importlib.metadata.version
    ## therefore, it's name is processed as either 'python-magic' or 'python-magic-bin' after find_spec

    for package in args:
        # spec = importlib.util.find_spec(package)
        match package:
            case ('magic' as pkg) if (spec := importlib.util.find_spec('magic')):
                packages_dict[pkg]["version"] = version('python-magic-bin' if sys.platform == "win32" else 'python-magic')
                packages_dict[pkg]["searchLoc"] = (spec.submodule_search_locations or [""])[0]
                packages_dict[pkg]["installed"] = "[green]Installed[/green]"

            case ('pymupdf' as pkg) if (spec := importlib.util.find_spec('pymupdf')):
                packages_dict[pkg]["version"] = version(pkg)
                packages_dict[pkg]["searchLoc"] = (spec.submodule_search_locations or [""])[0]
                packages_dict[pkg]["installed"] = "[green]Installed[/green]"

            case 'ghostscript':
                from pdfsimuti.utils import rtn_gs_name
                gs_name = rtn_gs_name()
                try: 
                    result = subprocess.run([gs_name, '--version'], capture_output=True, text=True)
                except FileNotFoundError: return 0
                
                if result.stdout:
                    bin_loc = shutil.which(gs_name) # get location of the package
                    packages_dict["ghostscript"]["version"] = result.stdout.rstrip() # rstrip gets rid of the /n that comes from the capture_output
                    packages_dict["ghostscript"]["searchLoc"] = bin_loc
                    packages_dict["ghostscript"]["installed"] = "[green]Installed[/green]"


def checkhealth():
    from rich import prompt, tree, padding, box
    from rich.panel import Panel
    from rich.console import Console, Group
    from pdfsimuti.main import __version__

    console = Console()
    package_tree = tree.Tree(Panel("Package Status", expand=False), guide_style="bold bright_blue")

    spec = importlib.util.find_spec("pdfsimuti")
    pdfsimuti_package_stat: str | None = (
        spec.submodule_search_locations[0]
        if spec and spec.submodule_search_locations
        else ""
    )

    # update package status
    update_packages_dict('pymupdf', 'magic', 'ghostscript')

    for package in packages_dict.items():
        pac = package_tree.add(Panel(package[0], expand=False))
        pac.add("[u][b]Status:[/b][/u] " + package[1]["installed"])
        pac.add("[u][b]Version:[/b][/u] " + package[1]["version"])
        pac.add("[u][b]Source:[/b][/u] " + f"[i]{package[1]["searchLoc"]}[/i]") 


    main_tree = tree.Tree(Panel(f"pdfSimuti v{__version__} checkhealth\n[i]a python typer + rich simple pdf utility tool.[/i]", expand=False, box=box.DOUBLE), guide_style="underline2")
    main_tree.add(console.render_str("[u]Installed source[/u]: " + f"{pdfsimuti_package_stat}"))
    main_tree.add(package_tree)

    renderable_group = Group(
        main_tree,
        console.render_str("\n\n[green]Made by average-fox[/green]\n[i]Send suggestions, bugs or issues etc. on GitHub[/i]")
    )

    with console.screen():
        console.print(padding.Padding(renderable_group, (1,1)))
        prompt.Prompt.ask("\nEnter any key to continue")