import typer
from . import merge

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_show_locals=False, rich_markup_mode="rich"
)


@app.callback()
def callback():
    """
    A very simple PDF utility tool written in Python using Typer.
    """


# why app.command()(app.app)? See: https://github.com/fastapi/typer/issues/178
app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF.")(
    merge.merge
)
