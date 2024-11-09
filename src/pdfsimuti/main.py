import typer
from . import merge, compress

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_show_locals=False, rich_markup_mode="rich"
)


@app.callback()
def callback():
    """
    A very simple PDF utility tool written in Python using Typer.
    """


# why app.command()(app.app)? See: https://github.com/fastapi/typer/issues/178
app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF")(merge.merge)
app.command(help="PDF file compression using [i]Ghostscript[/i]", epilog="""
            Inspiration taken from [link=https://github.com/theeko74/pdfc]pdfc by theeko[/link]. \n
            Be sure to [yellow]stargraze[/yellow] their repository!
            """)(compress.compress)
