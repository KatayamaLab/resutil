from __future__ import annotations

import re
from datetime import datetime
from os.path import join
from typing import Optional, Tuple

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Resize
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from ..config_file import Config, create_ex_yaml
from ..core import (
    download,
    download_with_dependency,
    get_ex_dir_names,
    initialize,
    remove_local,
    remove_remote,
    upload,
    upload_with_dependency,
)
from ..ex_dir import (
    change_comment,
    create_ex_dir,
    find_undownloaded_ex_dirs,
    find_unuploaded_ex_dirs,
)
from ..utils import verify_comment


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _parse_experiment(name: str) -> dict:
    """Parse an experiment directory name into parts."""
    parts = name.split("_", 2)
    base26 = parts[0] if len(parts) >= 1 else ""
    timestamp_raw = parts[1] if len(parts) >= 2 else ""
    comment = parts[2] if len(parts) >= 3 else ""

    date_str = ""
    if timestamp_raw:
        try:
            dt = datetime.strptime(timestamp_raw, "%Y%m%dT%H%M%S")
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            date_str = timestamp_raw

    return {
        "name": name,
        "base26": base26,
        "timestamp": timestamp_raw,
        "date": date_str,
        "comment": comment,
    }


# ---------------------------------------------------------------------------
# Action Menu (single selection)
# ---------------------------------------------------------------------------

class ActionMenuScreen(ModalScreen[Optional[str]]):
    """Modal action menu for a single experiment."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ActionMenuScreen {
        align: center middle;
    }
    #action-dialog {
        width: 50;
        height: auto;
        max-height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #action-dialog .action-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #action-dialog .action-item {
        padding: 0 1;
        height: 1;
    }
    #action-dialog .action-item:hover {
        background: $accent;
    }
    #action-dialog .action-item.highlighted {
        background: $accent;
    }
    #action-dialog .action-item.destructive {
        color: $error;
    }
    #action-dialog .action-item.push-action {
        color: $success;
    }
    #action-dialog .action-item.pull-action {
        color: #00bfff;
    }
    #action-dialog .action-item.edit-action {
        color: #5599ff;
    }
    #action-dialog .action-item.cancel-action {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        ex_name: str,
        has_local: bool,
        has_remote: bool,
        multi: bool = False,
        count: int = 1,
        any_local_only: bool = False,
        any_remote_only: bool = False,
    ):
        super().__init__()
        self.ex_name = ex_name
        self.has_local = has_local
        self.has_remote = has_remote
        self.multi = multi
        self.count = count
        self.any_local_only = any_local_only
        self.any_remote_only = any_remote_only
        self._items: list[tuple[str, str, str]] = []  # (action_id, label, css_class)
        self._cursor = 0

    def compose(self) -> ComposeResult:
        self._items = []

        if self.multi:
            title = f"Actions ({self.count} selected)"
            if self.any_local_only:
                self._items.append(("push", "⬆ Push local-only to remote", "push-action"))
            if self.any_remote_only:
                self._items.append(("pull", "⬇ Pull remote-only to local", "pull-action"))
        else:
            comment = _parse_experiment(self.ex_name)["comment"]
            title = f"Actions: {comment or self.ex_name}"
            if self.has_local and not self.has_remote:
                self._items.append(("push", "⬆ Push to remote", "push-action"))
            elif not self.has_local and self.has_remote:
                self._items.append(("pull", "⬇ Pull from remote", "pull-action"))
            if self.has_local and self.has_remote and not self.multi:
                pass  # synced — no push/pull needed
            if not self.multi:
                self._items.append(("comment", "✏ Change comment", "edit-action"))

        self._items.append(("remove", "🗑 Remove", "destructive"))
        self._items.append(("cancel", "✕ Cancel", "cancel-action"))

        with Vertical(id="action-dialog"):
            yield Label(title, classes="action-title")
            for i, (action_id, label, css_cls) in enumerate(self._items):
                classes = f"action-item {css_cls}"
                if i == 0:
                    classes += " highlighted"
                yield Label(label, id=f"act-{action_id}", classes=classes)

    def _update_highlight(self) -> None:
        for i, (action_id, _, _) in enumerate(self._items):
            widget = self.query_one(f"#act-{action_id}", Label)
            if i == self._cursor:
                widget.add_class("highlighted")
            else:
                widget.remove_class("highlighted")

    def key_up(self) -> None:
        self._cursor = max(0, self._cursor - 1)
        self._update_highlight()

    def key_down(self) -> None:
        self._cursor = min(len(self._items) - 1, self._cursor + 1)
        self._update_highlight()

    def key_enter(self) -> None:
        action_id = self._items[self._cursor][0]
        if action_id == "cancel":
            self.dismiss(None)
        else:
            self.dismiss(action_id)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Remove Options Screen
# ---------------------------------------------------------------------------

class RemoveScreen(ModalScreen[Optional[Tuple[bool, bool]]]):
    """Choose where to remove from: local / remote."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    RemoveScreen {
        align: center middle;
    }
    #remove-dialog {
        width: 50;
        height: auto;
        max-height: 16;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    #remove-dialog .rm-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    #remove-dialog .rm-option {
        padding: 0 1;
        height: 1;
    }
    #remove-dialog .rm-option:hover {
        background: $accent;
    }
    #remove-dialog .rm-option.highlighted {
        background: $accent;
    }
    #remove-dialog .rm-option.disabled {
        color: $text-muted;
    }
    #remove-dialog .rm-cancel {
        padding: 0 1;
        height: 1;
        color: $text-muted;
    }
    #remove-dialog .rm-cancel:hover {
        background: $accent;
    }
    #remove-dialog .rm-cancel.highlighted {
        background: $accent;
    }
    """

    def __init__(self, ex_name: str, has_local: bool, has_remote: bool, multi: bool = False, count: int = 1):
        super().__init__()
        self.ex_name = ex_name
        self.has_local = has_local
        self.has_remote = has_remote
        self.multi = multi
        self.count = count
        self.rm_local = has_local
        self.rm_remote = False
        self._cursor = 0  # 0=local, 1=remote, 2=confirm, 3=cancel
        self._items: list[str] = []  # ["local", "remote", "confirm", "cancel"]

    def compose(self) -> ComposeResult:
        title = f"Remove ({self.count} selected)" if self.multi else f"Remove: {_parse_experiment(self.ex_name)['comment'] or self.ex_name}"

        self._items = ["local", "remote", "confirm", "cancel"]

        with Vertical(id="remove-dialog"):
            yield Label(title, classes="rm-title")
            yield Label(self._local_label(), id="rm-local", classes="rm-option highlighted" + (" disabled" if not self.has_local else ""))
            yield Label(self._remote_label(), id="rm-remote", classes="rm-option" + (" disabled" if not self.has_remote else ""))
            yield Label("", id="rm-spacer")
            yield Label("▸ Confirm delete", id="rm-confirm", classes="rm-option")
            yield Label("  ✕ Cancel", id="rm-cancel", classes="rm-cancel")

    def _local_label(self) -> str:
        check = "☒" if self.rm_local else "☐"
        suffix = " (not available)" if not self.has_local else ""
        return f"  {check} Local{suffix}"

    def _remote_label(self) -> str:
        check = "☒" if self.rm_remote else "☐"
        suffix = " (not available)" if not self.has_remote else ""
        return f"  {check} Remote{suffix}"

    def _update_display(self) -> None:
        self.query_one("#rm-local", Label).update(self._local_label())
        self.query_one("#rm-remote", Label).update(self._remote_label())

        for i, item_id in enumerate(self._items):
            widget = self.query_one(f"#rm-{item_id}", Label)
            if i == self._cursor:
                widget.add_class("highlighted")
            else:
                widget.remove_class("highlighted")

    def key_up(self) -> None:
        self._cursor = max(0, self._cursor - 1)
        self._update_display()

    def key_down(self) -> None:
        self._cursor = min(len(self._items) - 1, self._cursor + 1)
        self._update_display()

    def key_space(self) -> None:
        self._toggle_current()

    def key_enter(self) -> None:
        item = self._items[self._cursor]
        if item in ("local", "remote"):
            self._toggle_current()
        elif item == "confirm":
            if self.rm_local or self.rm_remote:
                self.dismiss((self.rm_local, self.rm_remote))
            else:
                self.notify("Select at least one target", severity="warning")
        elif item == "cancel":
            self.dismiss(None)

    def _toggle_current(self) -> None:
        item = self._items[self._cursor]
        if item == "local" and self.has_local:
            self.rm_local = not self.rm_local
        elif item == "remote" and self.has_remote:
            self.rm_remote = not self.rm_remote
        self._update_display()

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Confirm Screen
# ---------------------------------------------------------------------------

class ConfirmScreen(ModalScreen[bool]):
    """Simple yes/no confirmation dialog."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 55;
        height: auto;
        max-height: 18;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    #confirm-dialog .confirm-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    #confirm-dialog .confirm-body {
        margin-bottom: 1;
        color: $text-muted;
    }
    #confirm-dialog .confirm-btn {
        padding: 0 1;
        height: 1;
    }
    #confirm-dialog .confirm-btn:hover {
        background: $accent;
    }
    #confirm-dialog .confirm-btn.highlighted {
        background: $accent;
    }
    #confirm-dialog .confirm-yes {
        color: $error;
    }
    #confirm-dialog .confirm-no {
        color: $text-muted;
    }
    """

    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__()
        self.message_text = message
        self.details = details or []
        self._cursor = 1  # default to No

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("Confirm Deletion", classes="confirm-title")
            yield Label(self.message_text)
            for d in self.details:
                yield Label(f"  {d}", classes="confirm-body")
            yield Label("")
            yield Label("  Yes, delete", id="confirm-yes", classes="confirm-btn confirm-yes")
            yield Label("▸ No, cancel", id="confirm-no", classes="confirm-btn confirm-no highlighted")

    def _update_highlight(self) -> None:
        yes_w = self.query_one("#confirm-yes", Label)
        no_w = self.query_one("#confirm-no", Label)
        if self._cursor == 0:
            yes_w.add_class("highlighted")
            yes_w.update("▸ Yes, delete")
            no_w.remove_class("highlighted")
            no_w.update("  No, cancel")
        else:
            no_w.add_class("highlighted")
            no_w.update("▸ No, cancel")
            yes_w.remove_class("highlighted")
            yes_w.update("  Yes, delete")

    def key_up(self) -> None:
        self._cursor = 0
        self._update_highlight()

    def key_down(self) -> None:
        self._cursor = 1
        self._update_highlight()

    def key_left(self) -> None:
        self._cursor = 0
        self._update_highlight()

    def key_right(self) -> None:
        self._cursor = 1
        self._update_highlight()

    def key_enter(self) -> None:
        self.dismiss(self._cursor == 0)

    def action_cancel(self) -> None:
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Comment Input Screen
# ---------------------------------------------------------------------------

class CommentInputScreen(ModalScreen[Optional[str]]):
    """Input a new comment."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    CommentInputScreen {
        align: center middle;
    }
    #comment-dialog {
        width: 60;
        height: auto;
        max-height: 12;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #comment-dialog .comment-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #comment-dialog .comment-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, current_comment: str = ""):
        super().__init__()
        self.current_comment = current_comment

    def compose(self) -> ComposeResult:
        with Vertical(id="comment-dialog"):
            yield Label("Change Comment", classes="comment-title")
            yield Input(value=self.current_comment, placeholder="Enter new comment", id="comment-input")
            yield Label("Enter: confirm  Esc: cancel", classes="comment-hint")

    def on_mount(self) -> None:
        self.query_one("#comment-input", Input).focus()

    @on(Input.Submitted, "#comment-input")
    def on_submit(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if value and verify_comment(value):
            self.dismiss(value)
        elif value:
            self.notify("Invalid comment (max 200 chars, no special chars)", severity="error")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# New Experiment Screen
# ---------------------------------------------------------------------------

class NewExperimentScreen(ModalScreen[Optional[str]]):
    """Create a new experiment."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    NewExperimentScreen {
        align: center middle;
    }
    #new-exp-dialog {
        width: 60;
        height: auto;
        max-height: 12;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }
    #new-exp-dialog .new-exp-title {
        text-style: bold;
        color: $success;
        margin-bottom: 1;
    }
    #new-exp-dialog .new-exp-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="new-exp-dialog"):
            yield Label("New Experiment", classes="new-exp-title")
            yield Input(placeholder="Enter comment for new experiment", id="new-exp-input")
            yield Label("Enter: create  Esc: cancel", classes="new-exp-hint")

    def on_mount(self) -> None:
        self.query_one("#new-exp-input", Input).focus()

    @on(Input.Submitted, "#new-exp-input")
    def on_submit(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if verify_comment(value):
            self.dismiss(value)
        else:
            self.notify("Invalid comment (max 200 chars, no special chars)", severity="error")

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Help Screen
# ---------------------------------------------------------------------------

class HelpScreen(ModalScreen[Optional[str]]):
    """Keyboard shortcuts help."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("question_mark", "close", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-dialog {
        width: 52;
        height: auto;
        max-height: 22;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #help-dialog .help-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #help-dialog .help-section {
        text-style: bold;
        margin-top: 1;
    }
    #help-dialog .help-line {
        color: $text-muted;
    }
    #help-dialog .help-key {
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("Keyboard Shortcuts", classes="help-title")
            yield Label("Navigation", classes="help-section")
            yield Label("  ↑/↓  k/j    Move cursor", classes="help-line")
            yield Label("  Space        Toggle selection", classes="help-line")
            yield Label("  a            Select/deselect all (filtered)", classes="help-line")
            yield Label("  Enter        Open actions menu", classes="help-line")
            yield Label("")
            yield Label("Commands", classes="help-section")
            yield Label("  f /          Focus filter", classes="help-line")
            yield Label("  n            New experiment", classes="help-line")
            yield Label("  s            Settings (re-init)", classes="help-line")
            yield Label("  q  Ctrl+C    Quit", classes="help-line")
            yield Label("  ?            Show this help", classes="help-line")
            yield Label("")
            yield Label("Press any key to close", classes="help-line")

    def on_key(self) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class ResutilApp(App):
    """Resutil interactive experiment manager."""

    TITLE = "resutil"
    CSS = """
    Screen {
        background: $background;
    }
    #main-container {
        height: 1fr;
    }
    #table-container {
        height: 1fr;
    }
    #bottom-bar {
        height: 3;
        dock: bottom;
        padding: 0 1;
    }
    #filter-row {
        height: 1;
    }
    #shortcut-row {
        height: 1;
        color: $text-muted;
    }
    #hint-row {
        height: 1;
        color: $text-muted;
    }
    #filter-label {
        width: 9;
        color: $text-muted;
    }
    #filter-input {
        width: 1fr;
        height: 1;
        border: none;
        background: transparent;
    }
    #filter-input:focus {
        border: none;
    }
    .shortcut-key {
        text-style: bold;
        color: $success;
    }
    .shortcut-quit {
        text-style: bold;
        color: $error;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit", priority=True),
        Binding("question_mark", "show_help", "Help", priority=True),
        Binding("n", "new_experiment", "New", priority=True),
        Binding("f", "focus_filter", "Filter", priority=True),
        Binding("slash", "focus_filter", "Filter", priority=True),
        Binding("s", "settings", "Settings", priority=True),
        Binding("a", "select_all", "Select All", priority=True),
    ]

    filter_text: reactive[str] = reactive("", layout=False)

    def __init__(self, config: Config, storage):
        super().__init__()
        self.config = config
        self.storage = storage
        self._local_names: set[str] = set()
        self._remote_names: set[str] = set()
        self._all_experiments: list[str] = []
        self._selected: set[str] = set()
        self._wide_mode: bool = True

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield DataTable(id="exp-table", cursor_type="row")
        with Vertical(id="bottom-bar"):
            with Horizontal(id="filter-row"):
                yield Label("Filter: ", id="filter-label")
                yield Input(placeholder="type to filter...", id="filter-input")
            yield Static(
                "[bold green]F[/]ilter  [bold green]N[/]ew experiment  [bold green]S[/]ettings  [bold red]Q[/]uit       Enter actions  [bold]?[/]help",
                id="shortcut-row",
            )
            yield Static(
                "↑↓ move  Space select  a all",
                id="hint-row",
            )

    def on_mount(self) -> None:
        self.sub_title = self.config.project_name
        self._wide_mode = self.size.width >= 100
        self._refresh_data()
        self._build_table()

    def on_resize(self, event: Resize) -> None:
        new_wide = event.size.width >= 100
        if new_wide != self._wide_mode:
            self._wide_mode = new_wide
            self._build_table()

    # -- Data loading -------------------------------------------------------

    def _refresh_data(self) -> None:
        self._local_names = set(get_ex_dir_names(self.config.results_dir))
        self._remote_names = set(self.storage.get_all_experiment_names())
        self._all_experiments = sorted(
            list(self._local_names | self._remote_names), reverse=True
        )

    def _filtered_experiments(self) -> list[str]:
        if not self.filter_text:
            return self._all_experiments
        pattern = self.filter_text.lower()
        return [e for e in self._all_experiments if pattern in e.lower()]

    # -- Table building -----------------------------------------------------

    def _build_table(self) -> None:
        table = self.query_one("#exp-table", DataTable)
        table.clear(columns=True)

        table.add_column("", key="sel", width=3)
        table.add_column("LOCAL", key="local", width=5)
        table.add_column("REMOTE", key="remote", width=6)

        if self._wide_mode:
            table.add_column("DATE", key="date", width=18)
            table.add_column("DIRECTORY", key="dir")
            table.add_column("COMMENT", key="comment")
        else:
            table.add_column("DIRECTORY NAME", key="dir")

        for name in self._filtered_experiments():
            self._add_row(table, name)

        count = len(self._filtered_experiments())
        total = len(self._all_experiments)
        if self.filter_text:
            self.sub_title = f"{self.config.project_name} — {count}/{total} filtered"
        else:
            self.sub_title = f"{self.config.project_name} — {total} experiments"

    def _add_row(self, table: DataTable, name: str) -> None:
        has_local = name in self._local_names
        has_remote = name in self._remote_names
        selected = name in self._selected

        sel_mark = "[yellow]●[/]" if selected else " "
        local_mark = "[green]✔[/]" if has_local else "[dim]─[/]"
        remote_mark = "[green]✔[/]" if (has_remote and has_local) else "[#00bfff]✔[/]" if has_remote else "[dim]─[/]"

        parsed = _parse_experiment(name)

        if self._wide_mode:
            table.add_row(
                sel_mark,
                local_mark,
                remote_mark,
                f"[dim]{parsed['date']}[/]",
                name,
                parsed["comment"],
                key=name,
            )
        else:
            table.add_row(
                sel_mark,
                local_mark,
                remote_mark,
                name,
                key=name,
            )

    # -- Filter -------------------------------------------------------------

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self._build_table()

    def action_focus_filter(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            # Return focus to table
            self.query_one("#exp-table", DataTable).focus()

    def on_key(self, event) -> None:
        # When filter is focused, Escape clears it and returns to table
        try:
            filter_input = self.query_one("#filter-input", Input)
        except NoMatches:
            return
        if filter_input.has_focus and event.key == "escape":
            filter_input.value = ""
            self.query_one("#exp-table", DataTable).focus()
            event.prevent_default()
            event.stop()

    # -- Selection ----------------------------------------------------------

    def _get_cursor_experiment(self) -> str | None:
        table = self.query_one("#exp-table", DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            return str(row_key.value)
        except Exception:
            return None

    def key_space(self) -> None:
        name = self._get_cursor_experiment()
        if name is None:
            return
        if name in self._selected:
            self._selected.discard(name)
        else:
            self._selected.add(name)
        self._build_table()

    def action_select_all(self) -> None:
        filtered = set(self._filtered_experiments())
        if filtered.issubset(self._selected):
            # Deselect all filtered
            self._selected -= filtered
        else:
            self._selected |= filtered
        self._build_table()

    # -- Actions ------------------------------------------------------------

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter key on a row → open action menu."""
        self._open_actions()

    def _open_actions(self) -> None:
        if self._selected:
            names = [n for n in self._all_experiments if n in self._selected]
            any_local_only = any(n in self._local_names and n not in self._remote_names for n in names)
            any_remote_only = any(n not in self._local_names and n in self._remote_names for n in names)
            self.push_screen(
                ActionMenuScreen(
                    ex_name="",
                    has_local=False,
                    has_remote=False,
                    multi=True,
                    count=len(names),
                    any_local_only=any_local_only,
                    any_remote_only=any_remote_only,
                ),
                callback=self._on_action_chosen,
            )
        else:
            name = self._get_cursor_experiment()
            if name is None:
                return
            has_local = name in self._local_names
            has_remote = name in self._remote_names
            self.push_screen(
                ActionMenuScreen(
                    ex_name=name,
                    has_local=has_local,
                    has_remote=has_remote,
                ),
                callback=self._on_action_chosen,
            )

    def _on_action_chosen(self, action: str | None) -> None:
        if action is None:
            return

        if self._selected:
            names = [n for n in self._all_experiments if n in self._selected]
        else:
            name = self._get_cursor_experiment()
            names = [name] if name else []

        if not names:
            return

        if action == "push":
            self._do_push(names)
        elif action == "pull":
            self._do_pull(names)
        elif action == "comment":
            if len(names) == 1:
                self._do_comment(names[0])
        elif action == "remove":
            self._do_remove(names)

    @work(thread=True)
    def _do_push(self, names: list[str]) -> None:
        for name in names:
            if name in self._local_names and name not in self._remote_names:
                self.notify(f"Pushing {name}...")
                upload_with_dependency(name, self.config.results_dir, self.storage)
        self.app.call_from_thread(self._after_operation, "Push complete")

    @work(thread=True)
    def _do_pull(self, names: list[str]) -> None:
        for name in names:
            if name not in self._local_names and name in self._remote_names:
                self.notify(f"Pulling {name}...")
                download_with_dependency(name, self.config.results_dir, self.storage)
        self.app.call_from_thread(self._after_operation, "Pull complete")

    def _do_comment(self, name: str) -> None:
        parsed = _parse_experiment(name)
        self.push_screen(
            CommentInputScreen(current_comment=parsed["comment"]),
            callback=lambda new_comment: self._apply_comment(name, new_comment),
        )

    def _apply_comment(self, name: str, new_comment: str | None) -> None:
        if not new_comment:
            return
        self._apply_comment_worker(name, new_comment)

    @work(thread=True)
    def _apply_comment_worker(self, name: str, new_comment: str) -> None:
        has_local = name in self._local_names
        has_remote = name in self._remote_names
        if has_local:
            change_comment(self.config.results_dir, name, new_comment)
        if has_remote:
            self.storage.change_comment(name, new_comment)
        self.app.call_from_thread(self._after_operation, f"Comment changed")

    def _do_remove(self, names: list[str]) -> None:
        multi = len(names) > 1
        if multi:
            any_local = any(n in self._local_names for n in names)
            any_remote = any(n in self._remote_names for n in names)
        else:
            any_local = names[0] in self._local_names
            any_remote = names[0] in self._remote_names

        self.push_screen(
            RemoveScreen(
                ex_name=names[0] if not multi else "",
                has_local=any_local,
                has_remote=any_remote,
                multi=multi,
                count=len(names),
            ),
            callback=lambda result: self._on_remove_options(names, result),
        )

    def _on_remove_options(self, names: list[str], result: tuple[bool, bool] | None) -> None:
        if result is None:
            return
        rm_local, rm_remote = result

        targets = []
        if rm_local:
            targets.append("local")
        if rm_remote:
            targets.append("remote")
        target_str = " and ".join(targets)

        details = names[:5]
        if len(names) > 5:
            details.append(f"... and {len(names) - 5} more")

        self.push_screen(
            ConfirmScreen(
                message=f"Delete {len(names)} experiment(s) from {target_str}?",
                details=details,
            ),
            callback=lambda confirmed: self._execute_remove(names, rm_local, rm_remote, confirmed),
        )

    def _execute_remove(self, names: list[str], rm_local: bool, rm_remote: bool, confirmed: bool) -> None:
        if not confirmed:
            return
        self._execute_remove_worker(names, rm_local, rm_remote)

    @work(thread=True)
    def _execute_remove_worker(self, names: list[str], rm_local: bool, rm_remote: bool) -> None:
        if rm_local:
            local_names = [n for n in names if n in self._local_names]
            if local_names:
                remove_local(local_names, self.config.results_dir)
        if rm_remote:
            remote_names = [n for n in names if n in self._remote_names]
            if remote_names:
                remove_remote(remote_names, self.storage)
        self.app.call_from_thread(self._after_operation, "Remove complete")

    def _after_operation(self, message: str) -> None:
        self._selected.clear()
        self._refresh_data()
        self._build_table()
        self.notify(message, severity="information")

    # -- New experiment -----------------------------------------------------

    def action_new_experiment(self) -> None:
        self.push_screen(
            NewExperimentScreen(),
            callback=self._create_experiment,
        )

    def _create_experiment(self, comment: str | None) -> None:
        if not comment:
            return
        self._create_experiment_worker(comment)

    @work(thread=True)
    def _create_experiment_worker(self, comment: str) -> None:
        ex_name = create_ex_dir(datetime.now(), comment, self.config.results_dir)
        ex_dir_path = join(self.config.results_dir, ex_name)
        create_ex_yaml(ex_dir_path, [])
        self.app.call_from_thread(self._after_operation, f"Created: {ex_name}")

    # -- Settings / Help / Quit ---------------------------------------------

    def action_settings(self) -> None:
        self.notify("Run 'resutil init' to reconfigure settings", severity="warning")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_quit_app(self) -> None:
        self.exit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_interactive():
    """Launch the interactive TUI. Returns True if launched, False if not initialized."""
    try:
        config = Config()
        config.load()
    except FileNotFoundError:
        return False

    from ..storage import GCS, GDrive

    if config.storage_type in ("gcs", "gs"):
        storage = GCS(config.storage_config, config.project_name)
    elif config.storage_type == "gdrive":
        storage = GDrive(config.storage_config, config.project_name)
    else:
        print(f"Unknown storage type: {config.storage_type}")
        return False

    app = ResutilApp(config, storage)
    app.run()
    return True
