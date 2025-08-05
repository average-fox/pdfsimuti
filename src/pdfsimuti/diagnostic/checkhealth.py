import sys
import os
import textwrap # used for triple quote with indent without facing consequences
import shutil # used for getting ghostscriptapplication PATH variables
import subprocess # capture output

import importlib.util # getting package ModuleSpec
from importlib.metadata import version # for checking packages versions

from rich.console import Console
from rich.panel import Panel

import typer
from typing_extensions import Annotated

from pdfsimuti.utils import return_ghostscript_callname

console = Console()

packages_dict = {
    'pymupdf' : {
        "version": None, 
        "origin": None, 
        "searchLoc": None, 
        "installed": False,
        "description" : """
        [u][b]Description[/b][/u]: 
        Used as the main package for merging the files. Also have features to provide simple compressions.
        """},
    
    'magic' : {
        "version": None, 
        "origin": None,
        "searchLoc": None, 
        "installed": False,
        "description": """
        [u][b]Description[/b][/u]
        Used for checking if the file is actually the file format it claims to be. It checks for their mimecheck type.
        Without this, you cannot do something like the following~
        [code]pdfsimuti merge --no-mimecheck FILE1.pdf FILE2.pdf[/code]
        """},
    
    "ghostscript" : {
        "version": None,
        "origin": None,
        "searchLoc": None,
        "installed": False,
        "description": f"""
        [u][b]Description[/b][/u]: 
        GhostScript is a interpreter for PostScript and PDF. pdfSimUti doesn't install GhostScript because it's setup is different.
        Should you choose to compress PDF files using GhostScript
        instead of the default compression by "PyMuPDF", complete the setup below~
        
        [b][u]Installation[/u][/b]
        1. Go to [link=https://ghostscript.com/releases/gsdnld.html]gsdnld.html[/link] and download your ghostscript package
        2. Install your GhostScript package. 
        3. If you're on Windows, be sure to add your ghostscript package's "bin" directory to your PATH environments.
        
        [b][u]Verification[/u][/b]
        1. If you are on windows, run [code]gswin64c[/code] ([i]assuming you're on 64 bit[/i])
        2. If you are on linux, run [code]gs[/code] 
        3. If you are on something else, [link=https://github.com/foxtbirdy/PDFsimuti/issues/new]open an issue[/link]
        4. If you have done 1 & 2 and checkhealth  responds with "[i]Not Found[/i]", [link=https://github.com/foxtbirdy/PDFsimuti/issues/new]open an issue[/link]
        """
        }    
}


def get_gs_detail():
    """
    Get ghostscript details on your system.
    1. figure out what ghostscript you installed without telling you by figuring out your os and architecture
    2. calls subprocess to capture ghostscript version and other info
    3. calls shutil to locate ghostscript installed path
    4. updates 'packages_dict' for checkhealth feature
    
    if not found, nothing happens.
    """
    gs_name = return_ghostscript_callname()
    try: 
        result = subprocess.run([gs_name, '--version'], capture_output=True, text=True)
    except FileNotFoundError: return 0
    
    if result.stdout:
        bin_loc = shutil.which(gs_name) # get location of the package
        packages_dict["ghostscript"]["version"] = result.stdout.rstrip() # rstrip gets rid of the /n that comes from the capture_output
        packages_dict["ghostscript"]["origin"] = os.path.dirname(bin_loc) 
        packages_dict["ghostscript"]["searchLoc"] = bin_loc
        packages_dict["ghostscript"]["installed"] = True
    

def update_packages_dict(*args):
    """
    Update 'packages_dict' of their moduleSpec, installed location and other info.
    
    Note: magic in importlib.util.find_spec is not a valid name for importlib.metadata.version
    
    therefore, it's name is processed as either 'python-magic' or 'python-magic-bin' after find_spec
    """
    for package, item in packages_dict.items():
        if package not in args:
            pass
        
        spec = importlib.util.find_spec(package)
        if package == "magic" and spec != None: item["version"] = version('python-magic-bin' if sys.platform == "win32" else 'python-magic')
        # whoever decided magic should have different package names should be hanged.
        # this code is important because importlib.util and importlib.metadata.version are not the same!  
        
        if spec:
            if not item["version"]: item["version"] = version(package)
            item["origin"] = spec.origin
            item["searchLoc"] = "".join(spec.submodule_search_locations)
            item["installed"] = True


def verbose_level_1():
    """
    Verbose level 1 checks if the package is installed by getting it's origin location
    """
    panel_content = "\n".join(f"{key}: {'[green]Installed[/green]' if value['origin'] else '[red]Not Installed[/red]'}" for key, value in packages_dict.items())
    console.print(Panel(panel_content, title="[#00ffef]pdfSimUti checkhealth[/#00ffef]"))
    
    
def verbose_level_2():
    """
    Shows info of the package name, status, location of execuetion
    
    Displays in a panel form
    """
    from rich.table import Table
    
    table = Table(show_lines=True, show_edge=False, expand=True)
    table.add_column("Package Name", justify="center", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Location", justify="center")
    
    for package, item in packages_dict.items():
        table.add_row(package, "[green]Installed[/green]" if item['installed'] else "[red]Not Found[/red]", item['searchLoc'] if item['searchLoc'] else "[red]Not Found[/red]")
    console.print(Panel(table, title="[#00ffef]pdfSimUti checkhealth[/#00ffef]", padding=1))


def verbose_level_3():
    """
    everything in verbose_level_1() and verbose_level_2() with addition to description of the packages
    """
    for package, item in packages_dict.items():
        console.print(Panel(textwrap.dedent(f"""
        [u]Package name[/u]: [#00ffef]{package}[/#00ffef]
        [u]Package version[/u]: {f"[bold green]{item["version"]}[/bold green]" if item["version"] else "[red]Not found[/red]"}
        [u]Package Origin[/u]: {f"[#a2a2d0]{item["origin"]}[/#a2a2d0]" if item["origin"] else "[red]Not found[/red]"}
        [u]Package Search[/u]: {f"[#ff9f00]{item["searchLoc"]}[/#ff9f00]" if item["searchLoc"] else "[red]Not found[/red]"}
        {item["description"]}
        """).strip()))


def checkhealth(verbose: Annotated[int, typer.Option("--verbose", "-v", "-V", count=True, max=3, help="Verbose level")] = 1):
    """Typer assisted function runtime

    Args:
        verbose (Annotated[int, typer.Option, optional): Specify verbose levels. Defaults to True, max=3, help="Verbose level")]=1.
    """
    update_packages_dict('pymupdf', 'magic') # wrote this otherwise the code would have been ugly
    get_gs_detail() # created only for ghostscript
    match verbose:
        case 1: verbose_level_1()
        case 2: verbose_level_2()
        case 3: verbose_level_3()