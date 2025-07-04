import os
import sys
from functools import partial

file_path = os.path.abspath(__file__)
admin_panel_path = os.path.dirname(file_path)
server_root_path = os.path.dirname(admin_panel_path)
server_app_path = os.path.join(server_root_path, "app")
sys.path.insert(0, server_app_path)


from database import engine, session_maker  # noqa: E402
from models_db import ClientLogs, Hosts  # noqa: E402
from sqlalchemy import select  # noqa: E402
from textual import on  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.containers import Horizontal, Vertical  # noqa: E402
from textual.widgets import DataTable, Footer, Header, Log, Pretty  # noqa: E402


class AdminApp(App):
    CSS_PATH = "horizontal_layout.css"

    BINDINGS = [
        ("q", "quit", "Quit the application"),
        ("r", "refresh", "Refresh data"),
        ("a", "auto_refresh", "Auto refresh data"),
    ]

    def __init__(self):
        super().__init__()
        self.engine = engine
        self.session_maker = session_maker
        self.selected_host_id = None
        self._auto_timer = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal():
            yield DataTable(
                id="hosts_table",
                cursor_type="row",
                classes="box",
                zebra_stripes=True,
            )
            with Vertical(classes="box"):
                yield Log(id="host_logs", highlight=True, max_lines=1000)
                yield Pretty("", id="host_info")

        yield Footer()

    async def on_mount(self) -> None:
        hosts_table = self.query_one(DataTable)

        hosts_table.add_columns(
            "ID",
            "Computer Name",
            "OS",
            "Version",
            "Status",
            "Last Seen",
        )

        await self.load_hosts()

    async def load_hosts(self):
        hosts_table = self.query_one(DataTable)
        hosts_table.clear()

        async with self.session_maker() as session:
            result = await session.execute(
                select(Hosts).order_by(Hosts.last_seen.desc())
            )
            hosts = result.scalars().all()

        for host in hosts:
            hosts_table.add_row(
                host.id,
                host.computer_name,
                host.os_info,
                host.current_version,
                host.status,
                host.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
                key=str(host.id),
            )

    def action_refresh(self):
        self.run_worker(self.load_hosts, exclusive=True)

    async def action_auto_refresh(self):
        auto_timer = getattr(self, "_auto_timer", None)
        if auto_timer and not auto_timer.is_cancelled:
            auto_timer.stop()
            self._auto_timer = None
        else:
            self._auto_timer = self.set_interval(5, self.load_hosts, name="poll")

    @on(DataTable.RowHighlighted)
    def on_host_selected(self, event: DataTable.RowHighlighted):
        value = event.row_key.value
        if value is None:
            return
        host_id = int(value)

        work = partial(self.load_host_details, host_id)
        self.run_worker(work, exclusive=True)

    async def load_host_details(self, host_id: int):
        info_widget = self.query_one("#host_info", Pretty)
        logs_widget = self.query_one("#host_logs", Log)

        async with self.session_maker() as session:
            host = await session.get(Hosts, host_id)

            logs_result = await session.execute(
                select(ClientLogs)
                .where(ClientLogs.host_id == host_id)
                .order_by(ClientLogs.timestamp.asc())
            )
            logs = logs_result.scalars().all()

        if host:
            info_widget.update(host.to_dict())
        else:
            info_widget.update("Host not found.")

        logs_widget.clear()
        for log_entry in logs:
            logs_widget.write_line(
                f"[{log_entry.timestamp.strftime('%Y-%m-%d %H:%M')}] [{log_entry.log_level}] {log_entry.message}"
            )


if __name__ == "__main__":
    app = AdminApp()
    app.run()
