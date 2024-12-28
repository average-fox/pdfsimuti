import typer
from pdfsimuti import merge

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_show_locals=False, rich_markup_mode="rich"
)

@app.callback()
def callback():
    """
    A very simple PDF utility tool written in Python using Typer.
    """


# See: https://github.com/fastapi/typer/issues/178

app.command(
    short_help="Merges several PDFs into a super PDF",
    help="""
    Add ITEMS (PDF) to merge them together. Output file is 'merged.pdf' but you can change it using --ouput TEXT\n
    Tip: Pass '.' to include current directory.\n
    Pass PDFs only! Script will not accept folder path (yet)
    """
    )(merge.merge)

# app.command(
#     epilog="""
#     Inspiration taken from [link=https://github.com/theeko74/pdfc]pdfc by theeko[/link]\n
#     Be sure to [yellow]stargraze[/yellow] their repository!""",
#     help="[red][DOESN'T WORK YET][/red] Compression of PDF files",
#     )(compress.compress)
