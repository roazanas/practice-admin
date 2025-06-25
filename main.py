import json
import pathlib
from typing import Union
import asyncio

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.types import DirEntry
from textual.widgets import DataTable, DirectoryTree, Footer, Header


class LogsCheckerApp(App):
    CSS_PATH = "horizontal_layout.css"

    BINDINGS = [
        ("q", "quit", "Quit the application"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

        with Horizontal():
            yield DirectoryTree("./logs", classes="box machines")
            yield DataTable(classes="box logs")

    def on_ready(self) -> None:
        self.table = self.query_one(DataTable)

    @on(DirectoryTree.NodeHighlighted)
    async def on_node_highlighted(self, event: DirectoryTree.NodeHighlighted):
        entry = event.node.data
        if entry is None:
            return

        file_path = entry.path if hasattr(entry, "path") else entry
        if not file_path.is_file():
            return

        cols, rows = await asyncio.to_thread(self.get_cols_rows, file_path)
        self.table.clear(columns=True)
        self.table.add_columns(*cols)
        self.table.add_rows(rows)

    def get_cols_rows(
        self, entry: Union[DirEntry, pathlib.Path]
    ) -> tuple[list[str], list[list[str]]]:
        file_path = entry.path if isinstance(entry, DirEntry) else entry

        records: list[dict] = []
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue

        cols = list(records[0].keys())
        rows = [[r.get(c, "") for c in cols] for r in records]
        return cols, rows


if __name__ == "__main__":
    app = LogsCheckerApp()
    app.run()
