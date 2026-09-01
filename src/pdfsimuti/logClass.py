from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()

class Log:
    def __init__(self, console:Console=console):
        self.logger = logging.getLogger("pdfsimuti")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        if not self.logger.handlers:
            rich_handler = RichHandler(markup=True, console=console, show_path=False)
            rich_handler.setLevel(logging.DEBUG)
            rich_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(rich_handler)
