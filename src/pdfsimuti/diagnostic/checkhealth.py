import sys
import textwrap # for not making this a cursed code for outputs.

import importlib.util
from importlib.metadata import version

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import typer
from typing_extensions import Annotated

console = Console()

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
        1. Run 'pip install ghostscript'
        2. Run 'pip install setuptools'
        3. ([strong]IMPORTANT[/strong]) Go to [link=https://ghostscript.com/releases/gsdnld.html]gsdnld.html[/link] and download your ghostscript package
        4. Install your GhostScript package. 
        5. If you're on Windows, be sure to add your ghostscript package's "bin" directory to your PATH environments.
        
        [b][u]Verification[/u][/b]
        Traditionally, you cannot do '--version' for this feature. Follow the steps below~
        
        1. If you have cloned the repo, navigate to [i]pdfSimUti/samples/[/i] and [code]python run gs_sample.py[/code]
        2. If you have not cloned the repo, go to [link=https://pypi.org/project/ghostscript/]ghostscript's pypi[/link] and test out one of the examples.
        3. Alternatively, you can copy and run this code from [link=https://gitlab.com/pdftools/python-ghostscript/-/blob/develop/test/test_lowlevel.py?ref_type=heads]python-ghostscript[/link]"""
        }
    
}

def update_packages_dict():
    for package, item in packages_dict.items():
        
        spec = importlib.util.find_spec(package)
        if package == "magic" and spec != None: item["version"] = version('python-magic-bin' if sys.platform == "win32" else 'python-magic')
        # whoever decided magic should have different package names should be hanged.
        
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
    
    update_packages_dict() # wrote this otherwise the code would have been ugly
    match verbose:
        case 1: verbose_level_1()
        case 2: verbose_level_2()
        case 3: verbose_level_3()