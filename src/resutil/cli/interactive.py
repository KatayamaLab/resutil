from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime
from os.path import join
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.theme import Theme
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.css.query import NoMatches
from textual.events import Resize
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Header,
    Input,
    Label,
    Static,
)

from ..config_file import Config, create_ex_yaml
from ..core import (
    download_with_dependency,
    get_ex_dir_names,
    remove_local,
    upload_with_dependency,
)
from ..ex_dir import (
    change_comment,
    create_ex_dir,
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
# Confirm Screen
# ---------------------------------------------------------------------------

class ConfirmScreen(ModalScreen[bool]):
    """Simple yes/no confirmation dialog."""

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

    def on_key(self, event) -> None:
        event.stop()
        if event.key in ("up", "left"):
            self._cursor = 0
            self._update_highlight()
        elif event.key in ("down", "right"):
            self._cursor = 1
            self._update_highlight()
        elif event.key == "enter":
            self.dismiss(self._cursor == 0)
        elif event.key == "escape":
            self.dismiss(False)


# ---------------------------------------------------------------------------
# Comment Input Screen
# ---------------------------------------------------------------------------

class CommentInputScreen(ModalScreen[Optional[str]]):
    """Input a new comment."""

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

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


# ---------------------------------------------------------------------------
# New Experiment Screen
# ---------------------------------------------------------------------------

class NewExperimentScreen(ModalScreen[Optional[str]]):
    """Create a new experiment."""

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

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


# ---------------------------------------------------------------------------
# Help Screen
# ---------------------------------------------------------------------------

class HelpScreen(ModalScreen[Optional[str]]):
    """Keyboard shortcuts help."""

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
            yield Label("  Enter        Copy name to clipboard", classes="help-line")
            yield Label("")
            yield Label("Actions", classes="help-section")
            yield Label("  c            Change comment", classes="help-line")
            yield Label("  p            Push / Pull", classes="help-line")
            yield Label("  x            Delete local", classes="help-line")
            yield Label("")
            yield Label("Commands", classes="help-section")
            yield Label("  f /          Focus filter", classes="help-line")
            yield Label("  n            New experiment", classes="help-line")
            yield Label("  s            Settings (re-init)", classes="help-line")
            yield Label("  q  Ctrl+C    Quit", classes="help-line")
            yield Label("  ?            Show this help", classes="help-line")
            yield Label("")
            yield Label("Press any key to close", classes="help-line")

    def on_key(self, event) -> None:
        event.stop()
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class ResutilApp(App):
    """Resutil interactive experiment manager."""

    TITLE = "resutil"
    CSS = """
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
        Binding("c", "shortcut_comment", "Comment", priority=True),
        Binding("p", "shortcut_push_pull", "Push/Pull", priority=True),
        Binding("x", "shortcut_delete", "Delete local", priority=True),
    ]

    filter_text: reactive[str] = reactive("", layout=False)

    def __init__(self, config: Config, storage):
        super().__init__()
        self.register_theme(Theme(
            name="resutil-light",
            dark=False,
            primary="#004578",
            secondary="#0178D4",
            background="#FFFFFF",
            surface="#F5F5F5",
            panel="#EEEEEE",
        ))
        self.register_theme(Theme(
            name="resutil-dark",
            dark=True,
            primary="#0178D4",
            secondary="#004578",
            background="#1E1E1E",
            surface="#2D2D2D",
            panel="#363636",
        ))
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
                yield Label("[bold green]F[/]ilter: ", id="filter-label")
                yield Input(placeholder="type to filter...", id="filter-input")
            yield Static(
                "[bold green]N[/]ew  [bold green]C[/]omment  [bold green]P[/]ush/Pull  [bold red]X[/] delete  [bold green]S[/]ettings  [bold red]Q[/]uit  [bold]?[/]help",
                id="shortcut-row",
            )
            yield Static(
                "↑↓ move  [bold]Space[/] select  [bold]Enter[/] copy",
                id="hint-row",
            )

    def on_mount(self) -> None:
        self.theme = self._detect_theme()
        self.sub_title = self.config.project_name
        self._wide_mode = self.size.width >= 100
        self._refresh_data()
        self._build_table()
        self._scroll_to_bottom()

    @staticmethod
    def _detect_theme() -> str:
        """Detect terminal light/dark and return a Textual theme name."""
        # macOS: check system appearance (most reliable on macOS)
        try:
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-globalDomain", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=1,
            )
            # returncode == 0 means "Dark" value exists → dark mode
            # returncode != 0 means key not found → light mode
            if result.returncode != 0:
                return "resutil-light"
            return "resutil-dark"
        except Exception:
            pass
        # COLORFGBG: set by some terminals, format "fg;bg"
        colorfgbg = os.environ.get("COLORFGBG", "")
        if colorfgbg:
            parts = colorfgbg.split(";")
            try:
                bg = int(parts[-1])
                if bg >= 8:
                    return "resutil-light"
                return "resutil-dark"
            except ValueError:
                pass
        return "resutil-dark"

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
            list(self._local_names | self._remote_names)
        )

    def _filtered_experiments(self) -> list[str]:
        if not self.filter_text:
            return self._all_experiments
        pattern = self.filter_text.lower()
        return [e for e in self._all_experiments if pattern in e.lower()]

    # -- Table building -----------------------------------------------------

    def _build_table(self, cursor_hint: str | None = None) -> None:
        """Rebuild the table. cursor_hint overrides saved cursor name (for renames)."""
        table = self.query_one("#exp-table", DataTable)

        # Save current cursor and scroll position before rebuild
        cursor_name = cursor_hint
        saved_scroll_y = table.scroll_y
        if cursor_name is None and table.row_count > 0:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                cursor_name = str(row_key.value)
            except Exception:
                pass

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

        filtered = self._filtered_experiments()
        for name in filtered:
            self._add_row(table, name)

        # Restore cursor and scroll after layout recalculation
        target_row = None
        if cursor_name and table.row_count > 0:
            try:
                target_row = filtered.index(cursor_name)
            except ValueError:
                pass
        self.call_after_refresh(self._restore_table_state, target_row, saved_scroll_y)

        count = len(filtered)
        total = len(self._all_experiments)
        if self.filter_text:
            self.sub_title = f"{self.config.project_name} — {count}/{total} filtered"
        else:
            self.sub_title = f"{self.config.project_name} — {total} experiments"

    def _restore_table_state(self, target_row: int | None, scroll_y: float) -> None:
        table = self.query_one("#exp-table", DataTable)
        if target_row is not None and table.row_count > 0:
            table.cursor_coordinate = Coordinate(target_row, 0)
        table.scroll_y = min(scroll_y, table.virtual_size.height)

    def _scroll_to_bottom(self) -> None:
        table = self.query_one("#exp-table", DataTable)
        if table.row_count > 0:
            table.move_cursor(row=table.row_count - 1)

    def _add_row(self, table: DataTable, name: str) -> None:
        has_local = name in self._local_names
        has_remote = name in self._remote_names
        selected = name in self._selected

        sel_mark = "[yellow]●[/]" if selected else " "
        local_mark = "[green]✔[/]" if has_local else "[dim]─[/]"
        remote_mark = "[green]✔[/]" if (has_remote and has_local) else "[cyan]✔[/]" if has_remote else "[dim]─[/]"

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


    # -- Actions ------------------------------------------------------------

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter key → copy experiment name to clipboard."""
        name = self._get_cursor_experiment()
        if name:
            self._copy_to_clipboard(name)
            self.notify(f"Copied: {name}", severity="information")

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
            elif system == "Linux":
                try:
                    subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
                except FileNotFoundError:
                    subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True)
            elif system == "Windows":
                subprocess.run(["clip"], input=text.encode(), check=True)
        except Exception:
            pass

    @work(thread=True)
    def _do_push(self, names: list[str]) -> None:
        try:
            for name in names:
                if name in self._local_names and name not in self._remote_names:
                    self.notify(f"Pushing {name}...")
                    upload_with_dependency(name, self.config.results_dir, self.storage)
            self.app.call_from_thread(self._after_operation, "Push complete")
        except Exception as e:
            self.app.call_from_thread(self._after_error, f"Push failed: {e}")

    @work(thread=True)
    def _do_pull(self, names: list[str]) -> None:
        try:
            for name in names:
                if name not in self._local_names and name in self._remote_names:
                    self.notify(f"Pulling {name}...")
                    download_with_dependency(name, self.config.results_dir, self.storage)
            self.app.call_from_thread(self._after_operation, "Pull complete")
        except Exception as e:
            self.app.call_from_thread(self._after_error, f"Pull failed: {e}")

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
        try:
            has_local = name in self._local_names
            has_remote = name in self._remote_names
            # Compute new name for cursor tracking
            parts = name.split("_", 2)
            new_name = f"{parts[0]}_{parts[1]}_{new_comment}"
            if has_local:
                change_comment(self.config.results_dir, name, new_comment)
            if has_remote:
                self.storage.change_comment(name, new_comment)
            self.app.call_from_thread(self._after_operation_with_cursor, "Comment changed", new_name)
        except Exception as e:
            self.app.call_from_thread(self._after_error, f"Comment change failed: {e}")

    def _do_remove(self, names: list[str]) -> None:
        local_names = [n for n in names if n in self._local_names]
        if not local_names:
            self.notify("No local experiments to delete", severity="warning")
            return

        details = local_names[:5]
        if len(local_names) > 5:
            details.append(f"... and {len(local_names) - 5} more")

        self.push_screen(
            ConfirmScreen(
                message=f"Delete {len(local_names)} experiment(s) from local?",
                details=details,
            ),
            callback=lambda confirmed: self._execute_remove(local_names, confirmed),
        )

    def _execute_remove(self, names: list[str], confirmed: bool) -> None:
        if not confirmed:
            return
        self._execute_remove_worker(names)

    @work(thread=True)
    def _execute_remove_worker(self, names: list[str]) -> None:
        try:
            # Find the experiment just before the deleted ones for cursor placement
            removed = set(names)
            filtered = self._filtered_experiments()
            cursor_hint = None
            for i, n in enumerate(filtered):
                if n in removed:
                    # Take the one before the first removed entry
                    if i > 0:
                        cursor_hint = filtered[i - 1]
                    break

            remove_local(names, self.config.results_dir)
            if cursor_hint and cursor_hint not in removed:
                self.app.call_from_thread(self._after_operation_with_cursor, "Remove complete", cursor_hint)
            else:
                self.app.call_from_thread(self._after_operation, "Remove complete")
        except Exception as e:
            self.app.call_from_thread(self._after_error, f"Remove failed: {e}")

    def _after_operation(self, message: str) -> None:
        self._selected.clear()
        self._refresh_data()
        self._build_table()
        self.notify(message, severity="information")

    def _after_operation_with_cursor(self, message: str, cursor_hint: str) -> None:
        self._selected.clear()
        self._refresh_data()
        self._build_table(cursor_hint=cursor_hint)
        self.notify(message, severity="information")

    def _after_error(self, message: str) -> None:
        self._refresh_data()
        self._build_table()
        self.notify(message, severity="error")

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
        try:
            ex_name = create_ex_dir(datetime.now(), comment, self.config.results_dir)
            ex_dir_path = join(self.config.results_dir, ex_name)
            create_ex_yaml(ex_dir_path, [])
            self.app.call_from_thread(self._after_new_experiment, f"Created: {ex_name}")
        except Exception as e:
            self.app.call_from_thread(self._after_error, f"Create failed: {e}")

    def _after_new_experiment(self, message: str) -> None:
        self._selected.clear()
        self._refresh_data()
        self._build_table()
        self._scroll_to_bottom()
        self.notify(message, severity="information")

    # -- Keyboard shortcuts (C / P / X) ----------------------------------------

    def _get_target_names(self) -> list[str]:
        if self._selected:
            return [n for n in self._all_experiments if n in self._selected]
        name = self._get_cursor_experiment()
        return [name] if name else []

    def action_shortcut_comment(self) -> None:
        names = self._get_target_names()
        if len(names) == 1:
            self._do_comment(names[0])
        elif len(names) > 1:
            self.notify("Select a single experiment for comment", severity="warning")

    def action_shortcut_push_pull(self) -> None:
        names = self._get_target_names()
        if not names:
            return
        pushable = [n for n in names if n in self._local_names and n not in self._remote_names]
        pullable = [n for n in names if n not in self._local_names and n in self._remote_names]
        if pushable:
            self._do_push(pushable)
        elif pullable:
            self._do_pull(pullable)
        else:
            self.notify("Already synced", severity="information")

    def action_shortcut_delete(self) -> None:
        names = self._get_target_names()
        if names:
            self._do_remove(names)

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
    from rich import print as rprint

    try:
        config = Config()
        config.load()
    except FileNotFoundError:
        return False

    from ..storage import GCS, GDrive, ResutilServerStorage

    if config.storage_type in ("gcs", "gs"):
        storage = GCS(config.storage_config, config.project_name)
    elif config.storage_type == "gdrive":
        storage = GDrive(config.storage_config, config.project_name)
    elif config.storage_type == "server":
        try:
            storage = ResutilServerStorage(config.storage_config, config.project_name)
        except FileNotFoundError:
            rprint("🔐 Not logged in. Starting login...")
            from .cli_main import command_login

            class _Args:
                server_url = None
            command_login(_Args())

            # Retry after login
            try:
                storage = ResutilServerStorage(config.storage_config, config.project_name)
            except FileNotFoundError:
                rprint("[red]❌ Login failed. Run 'resutil login' manually.[/red]")
                return True
        except PermissionError as e:
            rprint(f"🔐 {e}")
            rprint("Re-authenticating...")
            from .cli_main import command_login

            class _Args:
                server_url = None
            command_login(_Args())

            try:
                storage = ResutilServerStorage(config.storage_config, config.project_name)
            except Exception as e2:
                rprint(f"[red]❌ Authentication failed: {e2}[/red]")
                return True
    else:
        rprint(f"Unknown storage type: {config.storage_type}")
        return False

    app = ResutilApp(config, storage)
    app.run()
    return True
