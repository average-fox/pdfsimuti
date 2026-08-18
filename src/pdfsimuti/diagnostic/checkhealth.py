import sys
import shutil # used for getting ghostscriptapplication PATH variables
import subprocess # capture output

import importlib.util # getting package ModuleSpec
from importlib.metadata import version # for checking packages versions

from typing import TypedDict

class packageInfo(TypedDict):
    version: str | None
    searchLoc: str | None
    installed: str

packages_dict:dict[str, packageInfo] = {
    'pymupdf' : {
        "version": None, 
        "searchLoc": None, 
        "installed": "[red]Not installed[/red]"
        },
    
    'magic' : {
        "version": None, 
        "searchLoc": None, 
        "installed": "[red]Not installed[/red]"
        },
    
    "ghostscript" : {
        "version": None,
        "searchLoc": None,
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


def checkhealth_output():
    from rich import prompt, tree, console, padding, panel

    console = console.Console()
    package_tree = tree.Tree("Package Status")

    # update package status
    update_packages_dict('pymupdf', 'magic', 'ghostscript')

    for package in packages_dict.items():
        pac = package_tree.add(package[0])
        pac.add("[u][b]Status:[/b][/u] " + package[1]["installed"])
        pac.add("[u][b]Version:[/b][/u] " + (package[1]["version"] or ""))
        pac.add("[u][b]Source:[/b][/u] " + f"[i]{package[1]["searchLoc"] or ""}[/i]") 

    another_tree = tree.Tree(panel.Panel("pdfSimuti", expand=False))
    another_tree.add(package_tree)

    with console.screen():
        console.print(padding.Padding(another_tree, (1,1)))
        prompt.Prompt.ask("\nContinue?")


def checkhealth():


    checkhealth_output()
