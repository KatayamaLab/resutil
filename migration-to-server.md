# resutil: サーバーモード移行ガイド

resutil に `storage_type: server` を追加し、resutil-server 経由で GCS にアクセスできるようにした。
これにより、ユーザーは GCS のサービスアカウントキーを持つ必要がなくなり、SSO（Google / Microsoft）でログインするだけで利用できる。

## 変更概要

### 新規ファイル

| ファイル | 内容 |
|---|---|
| `src/resutil/storage/server/__init__.py` | パッケージ初期化 |
| `src/resutil/storage/server/server.py` | `ResutilServerStorage` クラス |

### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `pyproject.toml` | `httpx>=0.27.0` を依存に追加 |
| `src/resutil/storage/__init__.py` | `ResutilServerStorage` を export に追加 |
| `src/resutil/core.py` | `initialize()` に `storage_type == "server"` の分岐を追加 |
| `src/resutil/config_file.py` | `server` 用のバリデーションを追加（`server_url`, `bucket_name`） |
| `src/resutil/cli/cli_main.py` | `resutil login` コマンド追加、`resutil init` に server 選択肢追加 |

## 仕組み

### 認証フロー

```
resutil login
  → resutil-server の /auth/login API を呼び出し、サインインページの URL を取得
  → ブラウザが開き、Google or Microsoft で SSO
  → Firebase JS SDK がトークンを取得
  → localhost の一時サーバーにリダイレクトしてトークンを受け取る
  → ~/.resutil/credentials.json に保存（パーミッション 600）
```

### データ操作フロー

```
resutil push/pull
  → ~/.resutil/credentials.json から id_token を読み込み
  → resutil-server の API に id_token 付きでリクエスト
  → サーバーが権限チェック後、署名付き URL を発行
  → CLI が署名付き URL で GCS に直接アップロード/ダウンロード
```

## 使い方

### 1. ログイン

```bash
# Google アカウントでログイン（デフォルト）
resutil login --server-url https://resutil-server-586113954845.asia-northeast1.run.app

# Microsoft アカウントでログイン
resutil login --provider microsoft --server-url https://resutil-server-586113954845.asia-northeast1.run.app

# resutil-conf.yaml に server_url が設定済みなら --server-url は省略可能
resutil login
resutil login --provider microsoft
```

### 2. プロジェクト初期化

```bash
resutil init
# storage_type の入力で "server" を選択
# server URL と bucket name を入力
```

### 3. resutil-conf.yaml の例

```yaml
project_name: MyProj
results_dir: results
storage_type: server
storage_config:
  server_url: https://resutil-server-586113954845.asia-northeast1.run.app
  bucket_name: resutil
```

### 4. 通常操作（既存コマンドがそのまま使える）

```bash
resutil list                    # リモートの実験一覧
resutil push experiment_name    # アップロード
resutil pull experiment_name    # ダウンロード
resutil rm -r experiment_name   # リモート削除
resutil comment old_name new    # コメント変更（リネーム）
```

## 既存の GCS モードからの移行

1. `resutil login` でサーバーにログイン
2. `resutil-conf.yaml` を編集:

```yaml
# Before
storage_type: gcs
storage_config:
  key_file_path: key.json
  backet_name: resutil

# After
storage_type: server
storage_config:
  server_url: https://resutil-server-586113954845.asia-northeast1.run.app
  bucket_name: resutil
```

3. `key.json`（サービスアカウントキー）は不要になるので削除可能

## ~/.resutil/credentials.json

```json
{
  "server_url": "https://resutil-server-586113954845.asia-northeast1.run.app",
  "id_token": "eyJhbGciOi...",
  "refresh_token": "AMf-vBw..."
}
```

- `id_token`: Firebase が発行する JWT（有効期限 1 時間）
- `refresh_token`: トークン更新用（未実装。期限切れ時は `resutil login` を再実行）
- ファイルパーミッション: `600`

## 未実装・今後の課題

- **トークン自動リフレッシュ**: 現状は id_token の期限が切れたら `resutil login` を再実行する必要がある。CLI 側で refresh_token を使った自動更新を実装予定
- **resutil-server 側のテスト**: サーバー側は 30 テスト通過済み（`uv run pytest -v`）
- **CLI 側のテスト**: `ResutilServerStorage` の単体テストを追加予定
