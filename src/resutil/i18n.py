"""Message localization (English / Japanese).

The language is chosen in this order:

1. ``RESUTIL_LANG`` environment variable (``ja`` or ``en``)
2. ``LC_ALL`` / ``LC_MESSAGES`` / ``LANG`` (``C`` and ``POSIX`` carry no preference)
3. The OS UI language (macOS ``AppleLanguages``, Windows UI language)
4. English

Messages are looked up by their English text, so an untranslated message is
shown in English.
"""

import os
import subprocess
import sys
from functools import lru_cache

SUPPORTED = ("en", "ja")


def _normalize(value):
    """Map a locale string such as ``ja_JP.UTF-8`` or ``ja-JP`` to a language code."""
    if not value:
        return None
    code = value.split(".", 1)[0].split("@", 1)[0].replace("-", "_").lower()
    if code in ("", "c", "posix"):
        return None
    lang = code.split("_", 1)[0]
    return lang or None


def _macos_language():
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for line in result.stdout.splitlines():
        item = line.strip().strip('(),"').strip()
        if item:
            return _normalize(item)
    return None


def _windows_language():
    try:
        import ctypes

        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore
    except Exception:
        return None
    # Primary language ID 0x11 is Japanese.
    return "ja" if langid & 0x3FF == 0x11 else "en"


@lru_cache(maxsize=1)
def _os_language():
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        lang = _normalize(os.environ.get(name))
        if lang:
            return lang
    if sys.platform == "darwin":
        lang = _macos_language()
        if lang:
            return lang
    elif sys.platform == "win32":
        lang = _windows_language()
        if lang:
            return lang
    return None


def get_language():
    lang = _normalize(os.environ.get("RESUTIL_LANG")) or _os_language()
    return lang if lang in SUPPORTED else "en"


def t(message, **kwargs):
    """Translate ``message`` and fill ``{placeholders}`` from kwargs."""
    if get_language() == "ja":
        message = JA.get(message, message)
    return message.format(**kwargs) if kwargs else message


JA = {
    # --- CLI help -----------------------------------------------------------
    "initialize resutil": "resutil を初期化する",
    "pull experiments": "実験をダウンロードする",
    "pull experiments without dependencies": "依存する実験を含めずにダウンロードする",
    "pull all experiments": "すべての実験をダウンロードする",
    "experiment(s) to pull": "ダウンロードする実験",
    "push experiments": "実験をアップロードする",
    "push experiments without dependencies": "依存する実験を含めずにアップロードする",
    "push all experiments": "すべての実験をアップロードする",
    "experiment(s) to push": "アップロードする実験",
    "add experiments": "実験を追加する",
    "comment of the experiment to add": "追加する実験のコメント",
    "add depending experiments": "依存する実験を指定する",
    "list remote experiments": "リモートの実験を一覧表示する",
    "remove experiments": "実験を削除する",
    "remove local experiment": "ローカルの実験を削除する",
    "remove remote experiment": "リモートの実験を削除する",
    "confirm deletion without prompting": "確認せずに削除する",
    "Login to resutil server via SSO": "SSO で resutil サーバーにログインする",
    "resutil server URL (uses resutil-conf.yaml if not specified)": (
        "resutil サーバーの URL(省略時は resutil-conf.yaml の設定を使用)"
    ),
    "Remove saved credentials": "保存された認証情報を削除する",
    "Change comment of experiment": "実験のコメントを変更する",
    # --- init ---------------------------------------------------------------
    "⚠️ Already initialized.": "⚠️ すでに初期化されています。",
    "  [yellow]resutil-conf.yaml[/yellow] already exists.": (
        "  [yellow]resutil-conf.yaml[/yellow] が既に存在します。"
    ),
    "  If you proceed, the existing file will be overwritten.": (
        "  続行すると既存のファイルは上書きされます。"
    ),
    "  Do you want to proceed?": "  続行しますか?",
    "Input project name [bold]({default})[/bold]: ": (
        "プロジェクト名を入力 [bold]({default})[/bold]: "
    ),
    "Input directory name to store results [bold]({default})[/bold]: ": (
        "結果を保存するディレクトリ名を入力 [bold]({default})[/bold]: "
    ),
    "Do you want to add .gitignore to {path}?": "{path} に .gitignore を追加しますか?",
    "Input storage_type ([bold]gcs[/bold]/gdrive/server): ": (
        "storage_type を入力 ([bold]gcs[/bold]/gdrive/server): "
    ),
    "Input key file_path [bold]({default})[/bold]: ": (
        "キーファイルのパスを入力 [bold]({default})[/bold]: "
    ),
    "Do you want to add {path} to .gitignore?": "{path} を .gitignore に追加しますか?",
    "Input bucket name: ": "バケット名を入力: ",
    "Input folder id of base dir: ": "ベースフォルダの ID を入力: ",
    "Input server URL [bold]({default})[/bold]: ": (
        "サーバーの URL を入力 [bold]({default})[/bold]: "
    ),
    "❌ Failed to connect to storage.": "❌ ストレージに接続できませんでした。",
    "❌ Failed to connect to server.": "❌ サーバーに接続できませんでした。",
    "⚠️ Not logged in yet. Run [bold]resutil login[/bold] after init.": (
        "⚠️ まだログインしていません。初期化後に [bold]resutil login[/bold] を実行してください。"
    ),
    "✅ Initialized.": "✅ 初期化しました。",
    # --- push / pull / list / rm / comment / login --------------------------
    "✅ Uploaded": "✅ アップロードしました",
    "✅ Downloaded": "✅ ダウンロードしました",
    "ℹ️ There are {n} other experiment directory(s) that have not been uploaded. Do you want to upload them?": (
        "ℹ️ 未アップロードの実験ディレクトリが {n} 件あります。アップロードしますか?"
    ),
    "ℹ️ There are {n} other experiment directory(s) that have not been downloaded. Do you want to download them?": (
        "ℹ️ 未ダウンロードの実験ディレクトリが {n} 件あります。ダウンロードしますか?"
    ),
    "✅ No experiment to upload.": "✅ アップロードする実験はありません。",
    "✅ No experiment to download.": "✅ ダウンロードする実験はありません。",
    "⚠️ Specify experiment name(s) or use -A option.": (
        "⚠️ 実験名を指定するか、-A オプションを使用してください。"
    ),
    "📝 Input comment for this experiment: ": "📝 この実験のコメントを入力: ",
    '⛔️ Comment string is invalid. It should be at most 200 UTF-8 bytes and not contain any of the following characters: \\ / : * ? " < > |': (
        '⛔️ コメントが不正です。UTF-8 で 200 バイト以内とし、次の文字は使えません: \\ / : * ? " < > |'
    ),
    "Invalid comment (maximum 200 UTF-8 bytes).": (
        "コメントが不正です(UTF-8 で最大 200 バイト)。"
    ),
    "📦 Remote experiment list": "📦 リモートの実験一覧",
    " Local |Remote | Experiment name": " ローカル | リモート | 実験名",
    "-------|-------|------------------------------": (
        "----------|----------|------------------------------"
    ),
    "   {local}  |  {remote}   | {name}": "    {local}    |    {remote}    | {name}",
    "local and remote": "ローカルとリモート",
    "local": "ローカル",
    "remote": "リモート",
    "Delete {names} ({scope})?": "{names} を削除しますか({scope})?",
    "Use --server-url for server login.": (
        "サーバーにログインするには --server-url を指定してください。"
    ),
    "Server does not support login state. Apply docs/server-login-state.patch to resutil-server and deploy it first.": (
        "サーバーがログインの state に対応していません。先に docs/server-login-state.patch を resutil-server に適用してデプロイしてください。"
    ),
    "🔐 Opening browser for login: {url}": "🔐 ログインのためブラウザを開きます: {url}",
    "Login failed: no valid callback within 120 seconds.": (
        "ログインに失敗しました: 120 秒以内に有効なコールバックがありませんでした。"
    ),
    "Login successful. You may close this window.": (
        "ログインに成功しました。このウィンドウは閉じて構いません。"
    ),
    "✅ Login successful!": "✅ ログインしました!",
    "✅ Logged out. Credentials removed.": "✅ ログアウトしました。認証情報を削除しました。",
    "ℹ️ No credentials found.": "ℹ️ 認証情報が見つかりません。",
    "✅ Renamed {old} to {new}": "✅ {old} を {new} に変更しました",
    # --- utils --------------------------------------------------------------
    "Please try again - {question}": "もう一度入力してください - {question}",
    "Invalid experiment name: {name!r}": "実験名が不正です: {name!r}",
    "Experiment must be a direct directory under {root}: {name}": (
        "実験は {root} の直下のディレクトリである必要があります: {name}"
    ),
    # --- core ---------------------------------------------------------------
    "Cannot reach {storage} storage (network unavailable): {error}": (
        "{storage} ストレージに接続できません(ネットワーク不通): {error}"
    ),
    "📦 Connected to {storage}": "📦 {storage} に接続しました",
    "Wrong storage type. Check your {file} file.": (
        "ストレージの種類が不正です。{file} を確認してください。"
    ),
    "Experiment directory does not exist: {path}": (
        "実験ディレクトリが存在しません: {path}"
    ),
    "Local experiment does not exist: {name}": "ローカルに実験が存在しません: {name}",
    "Remote experiment does not exist: {name}": "リモートに実験が存在しません: {name}",
    "Local experiment already exists: {name}": "ローカルに実験が既に存在します: {name}",
    "🗂️ Uploading: {name}": "🗂️ アップロード中: {name}",
    "🗂️ Downloading: {name}": "🗂️ ダウンロード中: {name}",
    "🗑️ Removing (local): {name}": "🗑️ 削除中(ローカル): {name}",
    "⚠️ {name} does not exist in the local directory.": (
        "⚠️ {name} はローカルに存在しません。"
    ),
    "⚠️ {name} does not exist in the remote directory.": (
        "⚠️ {name} はリモートに存在しません。"
    ),
    # --- config file --------------------------------------------------------
    "config file {path} does not exist.": "設定ファイル {path} が存在しません。",
    "results_dir {path} does not exist.": "results_dir {path} が存在しません。",
    "storage_type must be 'gcs', 'gdrive' or 'server'": (
        "storage_type は 'gcs'、'gdrive'、'server' のいずれかである必要があります"
    ),
    "storage_config must have '{key}' key": (
        "storage_config には '{key}' キーが必要です"
    ),
    # --- main (decorator) ---------------------------------------------------
    "📴 Switching to offline mode: results are kept locally without upload.": (
        "📴 オフラインモードに切り替えます: 結果はアップロードせずローカルに保存します。"
    ),
    "storage is unreachable (offline)": "ストレージに接続できません(オフライン)",
    "remote access is disabled (RESUTIL_NO_REMOTE/RESUTIL_DEBUG)": (
        "リモートアクセスが無効です(RESUTIL_NO_REMOTE/RESUTIL_DEBUG)"
    ),
    "Cannot run: dependency experiment(s) not found locally and {reason}: {names}. Run 'resutil pull <name>' while online, then retry.": (
        "実行できません: 依存する実験がローカルになく、{reason}: {names}。オンライン時に 'resutil pull <name>' を実行してから再試行してください。"
    ),
    "Cannot run: failed to download dependency experiment {name} because the network is unavailable: {error}": (
        "実行できません: ネットワークが利用できないため、依存する実験 {name} をダウンロードできませんでした: {error}"
    ),
    "RESUTIL_COMMENT is invalid (maximum 200 UTF-8 bytes).": (
        "RESUTIL_COMMENT が不正です(UTF-8 で最大 200 バイト)。"
    ),
    "⛔️ Invalid comment (maximum 200 UTF-8 bytes; no path separators or control characters).": (
        "⛔️ コメントが不正です(UTF-8 で最大 200 バイト。パス区切り文字や制御文字は使えません)。"
    ),
    "📁 Experiment directory: {path}": "📁 実験ディレクトリ: {path}",
    "⚠️ Checkpoint upload offline: {error}. Results remain at {path}.": (
        "⚠️ オフラインのためチェックポイントをアップロードできませんでした: {error}。結果は {path} に残っています。"
    ),
    "⚠️ Checkpoint upload failed: {error}. Results remain at {path}.": (
        "⚠️ チェックポイントのアップロードに失敗しました: {error}。結果は {path} に残っています。"
    ),
    "📴 Offline: results were not uploaded. They remain at {path}. Run 'resutil push {name}' when online.": (
        "📴 オフライン: 結果はアップロードされていません。{path} に残っています。オンライン時に 'resutil push {name}' を実行してください。"
    ),
    "📴 Offline: upload failed ({error}). Results remain at {path}. Run 'resutil push {name}' when online.": (
        "📴 オフライン: アップロードに失敗しました({error})。結果は {path} に残っています。オンライン時に 'resutil push {name}' を実行してください。"
    ),
    "❌ Upload failed. Results remain at {path}. Retry with 'resutil push {name}'.": (
        "❌ アップロードに失敗しました。結果は {path} に残っています。'resutil push {name}' で再試行してください。"
    ),
    "🚀 Running the main function...": "🚀 main 関数を実行しています...",
    "Execution failed. Delete local experiment?": (
        "実行に失敗しました。ローカルの実験を削除しますか?"
    ),
    "✅ Done": "✅ 完了",
    # --- storage ------------------------------------------------------------
    "Key file not found at {path}": "キーファイルが見つかりません: {path}",
    "Multiple project folders found; resolve duplicate folders first.": (
        "プロジェクトフォルダが複数見つかりました。先に重複を解消してください。"
    ),
    "Credentials not found at {path}. Run 'resutil login' first.": (
        "認証情報が {path} にありません。先に 'resutil login' を実行してください。"
    ),
    "Invalid server URL.": "サーバーの URL が不正です。",
    "Cannot refresh server credentials. Run 'resutil login' again.": (
        "サーバーの認証情報を更新できません。もう一度 'resutil login' を実行してください。"
    ),
    "ID token expired and no refresh token available. Run 'resutil login' again.": (
        "ID トークンの有効期限が切れ、リフレッシュトークンもありません。もう一度 'resutil login' を実行してください。"
    ),
    "ID token expired but api_key not found in credentials. Run 'resutil login' again.": (
        "ID トークンの有効期限が切れましたが、認証情報に api_key がありません。もう一度 'resutil login' を実行してください。"
    ),
    "Credentials belong to a different server. Run 'resutil login' for this server.": (
        "認証情報は別のサーバーのものです。このサーバーに対して 'resutil login' を実行してください。"
    ),
    "Authentication failed. Your token may have expired. Run 'resutil login' again.": (
        "認証に失敗しました。トークンの有効期限が切れている可能性があります。もう一度 'resutil login' を実行してください。"
    ),
    "Access denied. You don't have permission to access bucket '{bucket}'.\nRun 'resutil login' to authenticate.": (
        "アクセスが拒否されました。バケット '{bucket}' へのアクセス権限がありません。\n'resutil login' で認証してください。"
    ),
    # --- interactive TUI ----------------------------------------------------
    "Confirm Deletion": "削除の確認",
    "Yes, delete": "はい、削除します",
    "No, cancel": "いいえ、キャンセル",
    "Change Comment": "コメントの変更",
    "Enter new comment": "新しいコメントを入力",
    "Enter: confirm  Esc: cancel": "Enter: 確定  Esc: キャンセル",
    "Invalid comment (max 200 UTF-8 bytes, no path separators or control characters)": (
        "コメントが不正です(UTF-8 で最大 200 バイト。パス区切り文字や制御文字は使えません)"
    ),
    "New Experiment": "新しい実験",
    "Enter comment for new experiment": "新しい実験のコメントを入力",
    "Enter: create  Esc: cancel": "Enter: 作成  Esc: キャンセル",
    "Keyboard Shortcuts": "キーボードショートカット",
    "Navigation": "移動",
    "  ↑/↓  k/j    Move cursor": "  ↑/↓  k/j    カーソル移動",
    "  Space        Toggle selection": "  Space        選択の切り替え",
    "  Enter        Copy name to clipboard": "  Enter        名前をクリップボードにコピー",
    "Actions": "操作",
    "  c            Change comment": "  c            コメントを変更",
    "  p            Push / Pull": "  p            プッシュ / プル",
    "  x            Delete local": "  x            ローカルを削除",
    "Commands": "コマンド",
    "  f /          Focus filter": "  f /          フィルタに移動",
    "  n            New experiment": "  n            新しい実験",
    "  s            Settings (re-init)": "  s            設定(再初期化)",
    "  q  Ctrl+C    Quit": "  q  Ctrl+C    終了",
    "  ?            Show this help": "  ?            このヘルプを表示",
    "Press any key to close": "いずれかのキーで閉じる",
    "[bold green]F[/]ilter: ": "[bold green]F[/] 絞込: ",
    "type to filter...": "入力して絞り込み...",
    "[bold green]N[/]ew  [bold green]C[/]omment  [bold green]P[/]ush/Pull  [bold red]X[/] delete  [bold green]S[/]ettings  [bold red]Q[/]uit  [bold]?[/]help": (
        "[bold green]N[/] 新規  [bold green]C[/] コメント  [bold green]P[/] プッシュ/プル  [bold red]X[/] 削除  [bold green]S[/] 設定  [bold red]Q[/] 終了  [bold]?[/] ヘルプ"
    ),
    "↑↓ move  [bold]Space[/] select  [bold]Enter[/] copy": (
        "↑↓ 移動  [bold]Space[/] 選択  [bold]Enter[/] コピー"
    ),
    "LOCAL": "ローカル",
    "REMOTE": "リモート",
    "DATE": "日時",
    "DIRECTORY": "ディレクトリ",
    "COMMENT": "コメント",
    "DIRECTORY NAME": "ディレクトリ名",
    "{project} — v{version} — {count}/{total} filtered": (
        "{project} — v{version} — {count}/{total} 件を表示"
    ),
    "{project} — v{version} — {total} experiments": (
        "{project} — v{version} — 全 {total} 件"
    ),
    "Could not refresh remote experiments: {error}": (
        "リモートの実験を取得できませんでした: {error}"
    ),
    "Copied: {name}": "コピーしました: {name}",
    "Pushing {name}...": "プッシュ中: {name}...",
    "Pulling {name}...": "プル中: {name}...",
    "Push complete": "プッシュが完了しました",
    "Pull complete": "プルが完了しました",
    "Push failed: {error}": "プッシュに失敗しました: {error}",
    "Pull failed: {error}": "プルに失敗しました: {error}",
    "Comment changed": "コメントを変更しました",
    "Comment change failed: {error}": "コメントの変更に失敗しました: {error}",
    "No local experiments to delete": "削除できるローカルの実験がありません",
    "... and {n} more": "...ほか {n} 件",
    "Delete {n} experiment(s) from local?": "ローカルから {n} 件の実験を削除しますか?",
    "Remove complete": "削除が完了しました",
    "Remove failed: {error}": "削除に失敗しました: {error}",
    "Created: {name}": "作成しました: {name}",
    "Create failed: {error}": "作成に失敗しました: {error}",
    "Select a single experiment for comment": (
        "コメントを変更する実験を 1 つだけ選択してください"
    ),
    "Remote is unavailable; retry when connected.": (
        "リモートに接続できません。接続後に再試行してください。"
    ),
    "Already synced": "同期済みです",
    "Run 'resutil init' to reconfigure settings": (
        "設定を変更するには 'resutil init' を実行してください"
    ),
    "[red]Storage credentials are unavailable.[/red]": (
        "[red]ストレージの認証情報がありません。[/red]"
    ),
    "[red]Authentication failed: {error}[/red]": "[red]認証に失敗しました: {error}[/red]",
    "[red]Cannot connect to storage: {error}[/red]": (
        "[red]ストレージに接続できません: {error}[/red]"
    ),
}
