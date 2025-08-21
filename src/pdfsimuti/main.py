import typer
import importlib.metadata

from typing import Optional
from typing_extensions import Annotated

from pdfsimuti.features import merge, compress
from pdfsimuti.diagnostic import checkhealth

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False,
    context_settings={"help_option_names" : ["-h", "--help"]},
)

# See https://docs.python.org/3/library/importlib.metadata.html#distribution-versions
__version__ = importlib.metadata.version('pdfsimuti')


def version_callback(value:bool):
    # You have to use an argument 'bool' otherwise you will get a "Missing Command" error.
    if value:
        print(f"PDFSimuti {__version__}")
        raise typer.Exit()


@app.callback(epilog="Written by [link=www.github.com/foxtbirdy]foxtbirdy[/link] 🦊 with 💜")
def main(version: Annotated[
    Optional[bool],
    typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show version & exit")] = None,
    ):
    """
    A very simple PDF utility tool written in Python using Typer.
    """
    pass


# See: https://github.com/fastapi/typer/issues/178 
app.command(
    # short_help="",
    help="""
    Merges several PDFs into a super PDF.
    

 ___   __ _______ ______   _______ _______ 
|  |_|  |       |    _ | |       |       |
|       |    ___|   | || |    ___|    ___|
|       |   |___|   |_||_|   | __|   |___ 
|       |    ___|    __  |   ||  |    ___|
| ||_|| |   |___|   |  | |   |_| |   |___ 
|_|   |_|_______|___|  |_|_______|_______|

- Output file is 'merged.pdf' by default but you can change it using --ouput TEXT
- Tip: Pass '.' to include current directory.
- Tip: You can pass folder paths as well just like adding PDF filenames.
"""
    )(merge.merge)


app.command(
    help="""
    Compress PDF(s) into smaller sizes.


    _______ _______ __   __ _______ ______   _______ _______ _______ 
    |       |       |  |_|  |       |    _ | |       |       |       |
    |   ----|   _   |       |    _  |   | || |    ___|  _____|  _____|
    |  |    |  | |  |       |   |_| |   |_||_|   |___| |_____| |_____ 
    |  |    |  |_|  |       |    ___|    __  |    ___|_____  |_____  |
    |  |____|       | ||_|| |   |   |   |  | |   |___ _____| |_____| |
    |_______|_______|_|   |_|___|   |___|  |_|_______|_______|_______|
    
    """,
    epilog="""
    Please note.\n
    - Any commands given for GhostScript without [bold]--compressMethod[/bold] being added is automatically ignored.
    """)(compress.compress)


app.command(
    help="""
    Shows you the status of the packages required for the program.
    
    You don't have to install all of them. However, that would limit the program's capability.
    
    - Verbose level 1: Returns package presence or not.
    - Verbose level 2: Verbose 1 + package related details.
    - Verbose level 3: Verbose 1 + 2 + effect on the program.
    """
    )(checkhealth.checkhealth)