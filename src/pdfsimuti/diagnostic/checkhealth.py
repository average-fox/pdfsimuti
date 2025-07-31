import sys
import os
import textwrap # used for triple quote with indent without facing consequences
import shutil # used for getting ghostscriptapplication PATH variables
import struct # WINDOWS + ghostScript only. Required to get CPU bit since gswin64c and gswin32c exists
import subprocess 

import importlib.util
from importlib.metadata import version # for checking packages versions

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import typer
from typing_extensions import Annotated

console = Console()
gs_name = "gs"+"win" if sys.platform == "win32" else ""+"64c" if 8*struct.calcsize("P") == 64 and sys.platform == "win32"  else "32c"


def get_gs_detail():
    gs_name = "gs"
    if sys.platform == "win32":
        gs_name+="win"
        if 8*struct.calcsize("P"): gs_name+="64c" 
        else: gs_name+="32c"
        
    result = subprocess.run([gs_name, '--version'], capture_output=True, text=True)
    
    if result.stdout:
        bin_loc = shutil.which(gs_name)
        packages_dict["ghostscript"]["version"] = result.stdout.rstrip()
        packages_dict["ghostscript"]["origin"] = os.path.dirname(bin_loc)
        packages_dict["ghostscript"]["searchLoc"] = bin_loc
        packages_dict["ghostscript"]["installed"] = True
            
            
packages_dict = {
    'pymupdf' : {
        "version": None, 
        "origin": None, 
        "searchLoc": None, 
        "installed": False,
        "description" : """
        Used as the main package for merging the files. Also have features to provide simple compressions.
        """},
    
    'magic' : {
        "version": None, 
        "origin": None,
        "searchLoc": None, 
        "installed": False,
        "description": """
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
        
        """
        }
    
}

def update_packages_dict(*args):
    for package, item in packages_dict.items():
        if package not in args:
            pass
        
        spec = importlib.util.find_spec(package)
        if package == "magic" and spec != None: item["version"] = version('python-magic-bin' if sys.platform == "win32" else 'python-magic')
        # whoever decided magic should have different package names should be hanged.
        # this code is important because importlib don't understand 'magic' but version do. 
        
        if spec:
            if not item["version"]: item["version"] = version(package)
            item["origin"] = spec.origin
            item["searchLoc"] = "".join(spec.submodule_search_locations)
            item["installed"] = True


def verbose_level_1():
    panel_content = "\n".join(f"{key}: {'[green]Installed[/green]' if value['origin'] else '[red]Not Installed[/red]'}" for key, value in packages_dict.items())
    console.print(Panel(panel_content, title="pdfSimUti checkhealth"))
    
    
def verbose_level_2():
    table = Table(show_lines=True, show_edge=False, expand=True)
    table.add_column("Package Name", justify="center", no_wrap=True)
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Location", justify="center")
    
    for package, item in packages_dict.items():
        table.add_row(package, "[green]Installed[/green]" if item['installed'] else "[red]Not Found[/red]", item['searchLoc'] if item['searchLoc'] else "[red]Not Found[/red]")
    console.print(Panel(table, title="[#00ffef]pdfSimUti checkhealth[/#00ffef]", padding=1))


def verbose_level_3():
    for package, item in packages_dict.items():
        console.print(Panel(textwrap.dedent(f"""
        [u]Package name[/u]: [#00ffef]{package}[/#00ffef]
        [u]Package version[/u]: {f"[bold green]{item["version"]}[/bold green]" if item["version"] else "[red]Not found[/red]"}
        [u]Package Origin[/u]: {f"[#a2a2d0]{item["origin"]}[/#a2a2d0]" if item["origin"] else "[red]Not found[/red]"}
        [u]Package Search[/u]: {f"[#ff9f00]{item["searchLoc"]}[/#ff9f00]" if item["searchLoc"] else "[red]Not found[/red]"}

        [u][b]Description[/b][/u]: {item["description"]}
        """).strip()))


def checkhealth(verbose: Annotated[int, typer.Option("--verbose", "-v", "-V", count=True, max=3, help="Verbose level")] = 1):
    
    update_packages_dict('pymupdf', 'magic') # wrote this otherwise the code would have been ugly
    get_gs_detail()
    match verbose:
        case 1: verbose_level_1()
        case 2: verbose_level_2()
        case 3: verbose_level_3()