# Resutil

## Resutilとは

**Resutil**は、Pythonプロジェクトから得られた実験結果データを管理するためのユーティリティです。コードや入力データなどの依存関係と共に結果データを管理します。データはクラウドストレージ（Google Cloud Storage、Google Drive、または Resutil サーバー）に同期され、チームでの共有とコラボレーションが可能です。

## なぜResutilを選ぶのか？

- **シンプル**：インストールが簡単ですぐにプロジェクトに導入できます。
- **高い再現性**：プログラム、入力データ、実験結果を追跡します。
- **オープンソースかつ無料**：Resutilの今後のリリースに向けた開発に参加できます。

## 特徴

- プログラムの実行終了後に特定のディレクトリに保存された実験データをクラウド（Google Cloud Storage、Google Drive、または Resutil サーバー）に同期します。
- 実験を再現するために必要な情報をYAMLファイルに保存します。
  - 実行コマンド
  - 引数で指定された入力ファイル（resutilで管理しているフォルダ内のファイルのみ）
  - Gitのコミットハッシュ
  - コミットされていないファイル
- アップロードされていない実験データをアップロードできます。
- コマンドを使用してクラウドから実験データをダウンロードできます。
- 実行時にローカルに存在しない依存関係を自動的にダウンロードします。

## インストール

ターミナルを開いて以下を実行

```bash
pip install resutil
```

Google Cloud Storage 用のサービスアカウント鍵（後述の手順でダウンロード）を `key.json` としてプロジェクトルートに保存します。鍵の例:

```json
{
    "type": "service_account",
    "project_id": "your-gcp-project",
    "private_key_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "private_key": "-----BEGIN PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n-----END PRIVATE KEY-----\n",
    "client_email": "resutil-bot@your-gcp-project.iam.gserviceaccount.com",
    "client_id": "123456789012345678901",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
}
```

resutilを初期化します

```bash
$ cd your-project-root-directory
$ resutil init
Input project name (resutil): MyProj
Input directory name to store results (results): results
Do you want to add .gitignore to results? (Y/n): Y
Input storage_type (gcs/gdrive/server): gcs
Input key file_path (key.json): key.json
Do you want to add key.json to .gitignore? (Y/n): Y
Input bucket name: resutil
✅ Initialized.
```
バケット名は Cloud Storage のバケット名です。`resutil-conf.yaml`というファイルが作成されます。

プロジェクトのメイン関数を以下のように修正します：

```python
# Import resutil
import resutil

# Add decorator before the main function
@resutil.main()
def main_func(params):
    # A directory is automatically created, and its path is stored in params.ex_dir
    ex_dir = params.ex_dir 

    # Execute the program HERE🚀
    # Resutil will handle the rest

if __name__ == "__main__":
    main_func()
```


## 使用方法

引数なしで `resutil` を実行すると、実験を管理するための対話型TUIが起動します。サブコマンドを直接使うこともできます。

### 実験の実行

Resutilを組み込んだプログラムを実行します。まずコメントを求められ、時系列順のアルファベット、日時、コメントを名前に含む実験結果保存用のディレクトリが自動的に作成されます。
このディレクトリはzip圧縮され、プログラム終了後に指定されたクラウドストレージにアップロードされます。


```bash
$ python sample.py

✨ Runnning your code with Resutil

📦 Connected to Google Cloud Storage
  📁 Bucket name: resutil
  📁 Project dir: your_project

📝 Input comment for this experiment (press [tab] key to completion): nice-comment

🔍 Unstaged files will be stored in the result dir:
  - README.ja.md
  - README.md
🚀 Running the main function...

### Your code's output

🗂️ Uploading: aapfup_20240704T191555_nice-comment
ℹ️ There are 9 other experiment directory(s) that have not been uploaded.
✅ Done
```

## クラウドストレージ設定方法

ResutilはGoogle Cloud Storage（標準）、Google Drive、およびResutilサーバーをサポートしています。各サービスに接続するための手順は以下の通りです。

### Google Cloud Storage（推奨）

1. **GCPプロジェクトを作成／選択**: [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成するか既存を利用します。
2. **Cloud Storage API を有効化**: [APIライブラリ](https://console.cloud.google.com/apis/library)で「Cloud Storage」を検索し有効化します。
3. **バケットを作成**: [Cloud Storage ブラウザ](https://console.cloud.google.com/storage/browser)で「バケットを作成」を選び、名前（例: `resutil`）、クラス、リージョンを設定します。
4. **サービスアカウントを作成**: [IAM と管理 → サービスアカウント](https://console.cloud.google.com/iam-admin/serviceaccounts)で「サービスアカウントを作成」をクリックし、例: `resutil-bot` を作成します。
5. **権限付与**: バケットに対し `Storage Object Admin`（少なくとも `Storage Object User` + `Storage Legacy Bucket Reader`）ロールを付与します。
6. **鍵の作成とダウンロード**: サービスアカウント詳細の「キー」→「キーを追加」→「新しいキーを作成」→ 種類 `JSON` でダウンロードし、プロジェクトルートに `key.json` として保存（`.gitignore` へ追加推奨）。
7. **`resutil init` を実行**: ストレージ種別に `gcs` を選び、`key.json` とバケット名を入力します。

### Google Drive

1. [Google Drive](https://drive.google.com/)でフォルダを作成し、フォルダID（URL の `folders/` 以降）を控えます。
2. GCP でプロジェクトとサービスアカウントを作成し、JSON鍵をダウンロードします。
3. **Google Drive API** を有効化します。
4. 作成したフォルダをサービスアカウントの `client_email` で共有し、`編集者` 権限を付与します。
5. `resutil init` でストレージ種別に `gdrive` を選び、`key.json` とフォルダIDを入力します。

### Resutil サーバー

1. `resutil init` でストレージ種別に `server` を選び、サーバーURLとバケット名を入力します。
2. `resutil login` でSSOによる認証を行います。

## コマンド

### `resutil init`

`resutil init`は、プロジェクトフォルダ内に`resutil-conf.yaml`を作成します。例:

```yaml
project_name: MyProj
results_dir: results/
storage_type: gcs
storage_config:
  bucket_name: resutil  # バケット名
  key_file_path: key.json
```

### `resutil push`

`resutil push 実験名` はローカルの実験をアップロードし、同名のリモート実験があれば上書きします。`resutil push --all` は未送信またはローカルで変更された実験を送信します。

`resutil push [exp_name]`は、特定のディレクトリの実験データをクラウドにアップロードします。`resutil-exp.yaml`に含まれる依存ディレクトリは自動的にアップロードされます。`--no-dependency`オプションを使用すると、自動依存アップロードが制限されます。

`resutil push --all`は、すべての実験データをクラウドにアップロードします。

### `resutil pull`

`resutil pull`コマンドは、ローカルの結果ディレクトリに存在しない特定の実験データをクラウドからダウンロードするために使用されます。

`resutil pull [exp_name]`は、クラウドから実験ディレクトリをダウンロードします。`resutil-exp.yaml`に含まれる依存ディレクトリは自動的にダウンロードされます。`--no-dependency`オプションを使用すると、自動依存ダウンロードが制限されます。

`resutil pull --all`は、現在ローカルの結果ディレクトリに存在しないすべての実験データをクラウドからダウンロードします。

これは、特に複数の人が同じプロジェクトに取り組み、実験データを更新している場合に、ローカルデータをクラウドに保存されているデータと同期させるのに便利です。

### `resutil add`

`resutil add`コマンドは、コードを実行せずに実験ディレクトリを追加するために使用されます。

以下のように使用できます: `resutil add [コメント] -d [依存関係1] [依存関係2]...`。このコマンドは、"コメント"という名前の実験ディレクトリを追加し、その依存関係を設定します。依存関係は、この実験が依存する他の実験です。

例えば、`exp1`と`exp2`という2つの実験があり、新しい実験がそれらに依存している場合、次のコマンドで新しい実験を追加できます: `resutil add "新しい実験" -d exp1 exp2`。これにより、"新しい実験"という名前の新しい実験ディレクトリが作成され、`exp1`と`exp2`がその依存関係として設定されます。

### `resutil list`

`resutil list` コマンドはクラウドストレージ内の実験一覧を表示します。

### `resutil rm`

`resutil rm` コマンドは実験を削除します。次のように使用できます：`resutil rm [-l] [-r] EXPERIMENT1 [EXPERIMENT2]...`。`--local` または `-l` オプションはローカルの実験ディレクトリのみを削除し、`--remote` または `-r` オプションはクラウド上の実験データを削除します。オプションを指定しない場合、両方の実験データを削除します。

### `resutil comment` **実験的機能**

`resutil comment [EXPERIMENT] [COMMENT]` は、タイムスタンプに続いて実験名にコメントを追加または変更します。既存の実験名が存在する場合、ローカルとクラウドの両方の実験名が変更されます。Resutil は異なる実験名を異なる実験として認識するため、これは他のユーザーが既にプルしている同じ実験の名前には影響しないことに注意してください。

### `resutil login`

`resutil login` はResutilサーバーにSSOで認証します。認証情報は `~/.resutil/credentials.json` に保存されます。`--server-url` でサーバーURLを指定できますが、省略した場合は `resutil-conf.yaml` から読み取ります。

### `resutil logout`

`resutil logout` は保存された認証情報（`~/.resutil/credentials.json`）を削除します。

### `resutil --version`

`resutil --version` はインストールされているResutilのバージョンを表示します。

## 環境変数

Resutilを組み込んだコードを実行する際に、以下の環境変数を使用できます。

`RESUTIL_COMMENT` 実行開始時に求められるコメントを指定します。実行時にコメントを求められなくなります。

`RESUTIL_NO_INTERACTIVE` 非インタラクティブモードにします。実行時にユーザーへ問い合わせをしなくなります。バッチジョブとして実行する場合に利用します。`RESUTIL_COMMENT` が指定されていない場合には実験ディレクトリにコメントは付与されません。

`RESUTIL_NO_REMOTE` クラウドストレージへのアップロードを抑制します。

`RESUTIL_DEBUG` デバッグモードを有効にします。一時ディレクトリが実験ディレクトリとして使用され、クラウドストレージへのアップロードは行われません。

## チェックポイントの保存

長時間にわたる実行時に実験ディレクトリに入っているデータを一時的にアップロードしたい場合には`param.save_checkpoint()`を呼び出します。


## クラウドストレージのディレクトリ構成

```plaintext
<bucket root>
├── MyProj  # プロジェクトディレクトリ
│   ├── aakuqj_20240511T174522_ex1.zip  # 実験ディレクトリのzip
│   │   ├── resutil-exp.yaml            # 実験情報
│   │   └── data.txt                    # データ（例）
│   ├── aamxrp_20240606T135747_ex2.zip
│   │   ├── resutil-exp.yaml
│   │   ├── data.txt
│   │   └── uncommited_files       # コミットされていないファイル
│   │       └── main.py
│   ...
│   
├── OtherProj
│
...
```

実験ディレクトリは `xxxxxx_yyyymmddTHHMMSS_comment` の形式で、xxxxxxはタイムスタンプなので、シェルでの順序付けやタブ補完が容易です。

## resutil-exp.yaml [WIP]

各実験ディレクトリには、実験結果を再現するための情報を含む `resutil-exp.yaml` が含まれます。

```yaml
cmd: Execution command
params: Options at runtime
  hoo: xxx
  bar: 123
dependency: Dependencies (automatically extracted from directories in the command)
  - ex1
  - ex2
```


## リリース手順

`vX.Y.Z` タグのプッシュを契機に、
[Publish Python Package](.github/workflows/publish.yaml) がPyPIへ公開します。
GitHub Releaseは別途作成します。`uv`、Git、認証済みのGitHub CLI
（`gh auth login`）を用意し、リポジトリのActionsシークレットに
`PYPI_TOKEN` が設定されていることを確認してください。

以下はPOSIXシェル用のコマンドです。一連の作業を通して `VERSION` の値を保持してください。

1. 公開対象の変更を `main` にマージし、作業ツリーに未コミット変更がない状態にします。
   PyPIとタグの両方で未使用のバージョンを選びます。以下の `0.2.4` は例です。

   ```sh
   git switch main
   git pull --ff-only origin main
   VERSION=0.2.4
   ```

   `pyproject.toml` の `[project].version` を同じ値へ変更し、
   ロックファイルと環境を更新します。

   ```sh
   uv lock
   uv sync --locked
   ```

   `docs/releases/v${VERSION}.md` に変更内容、互換性への影響、アップグレード方法を記載します。
   [v0.2.3のリリースノート](docs/releases/v0.2.3.md)を参考にしてください。
   サーバー変更が必要な場合は、対応するサーバーを先にデプロイします。

2. テスト・静的検査を実行し、配布パッケージをビルドします。

   ```sh
   uv run pytest -q
   uv run black --check src tests
   uv run flake8 src tests
   uv run mypy src
   uv run mypy --platform win32 src
   uv build --no-sources
   uvx --from twine==6.2.0 twine check \
     "dist/resutil-${VERSION}.tar.gz" \
     "dist/resutil-${VERSION}-py3-none-any.whl"
   ```

   ローカルの `dist/` には過去のビルドが残る場合があるため、対象バージョンだけを検査します。
   wheelとsdistの `core-metadata-version` は、公開ワークフローで使用する
   Twineに対応した値を維持してください。

3. リリース用ファイルの差分を確認してコミット・プッシュし、mainのCI成功を確認します。

   ```sh
   git add pyproject.toml uv.lock "docs/releases/v${VERSION}.md"
   git diff --cached
   git commit -m "Release v${VERSION}"
   git push origin main
   gh run list --repo KatayamaLab/resutil --workflow tests.yaml --branch main
   ```

   ほかに公開対象の変更ファイルがあれば、コミット前に追加します。
   プッシュしたコミットの実行を選び、Linux・Windows、Python 3.10・3.12の
   全ジョブが成功するまで待ちます。
   `gh run watch RUN_ID --repo KatayamaLab/resutil --exit-status` の
   `RUN_ID` を一覧に表示された実行IDへ置き換えると、完了を監視できます。

4. 検証済みのコミットにタグを付けてプッシュし、PyPI公開を開始します。

   ```sh
   git tag -a "v${VERSION}" -m "Resutil v${VERSION}"
   git push origin "v${VERSION}"
   ```

   タグのプッシュでテストと公開の両ワークフローが起動します。
   公開処理では再検査、ビルド、配布メタデータ検査、`dist` Actionsアーティファクトの保存、
   PyPIへのアップロードが実行されます。

5. 同じタグとリリースノートを使ってGitHub Releaseを作成します。

   ```sh
   gh release create "v${VERSION}" --repo KatayamaLab/resutil \
     --verify-tag --title "v${VERSION}" \
     --notes-file "docs/releases/v${VERSION}.md" --latest
   ```

6. 両ワークフローの成功と、公開されたパッケージを確認します。

   ```sh
   gh run list --repo KatayamaLab/resutil --branch "v${VERSION}"
   gh release view "v${VERSION}" --repo KatayamaLab/resutil
   uvx --from "resutil==${VERSION}" resutil --version
   ```

   各実行は `gh run watch RUN_ID --repo KatayamaLab/resutil --exit-status` で確認できます。
   [PyPI](https://pypi.org/project/resutil/)のバージョンと
   [GitHub Releases](https://github.com/KatayamaLab/resutil/releases)の内容も確認してください。
   公開済みのPyPIバージョンは上書きできないため、修正版には新しいバージョンを付けます。
   公開済みタグを別のコミットへ付け替えないでください。

## 安全性と追加設定

- `resutil rm` は削除前に確認します。スクリプトでは `--yes` を指定できます。
- `RESUTIL_NO_REMOTE` は認証とチェックポイントを含むアップロードを抑制します。
  旧表記 `RESUTIIL_REMOTE` も互換用に受け付けます。
- `RESUTIL_DEBUG` は実行ごとの一時ディレクトリを使用し、終了時に削除します。
- `RESUTIL_TIMEZONE=Asia/Tokyo` のようにIANAタイムゾーンを指定できます。
- `RESUTIL_STORAGE_TYPE`、`RESUTIL_GCS_BUCKET_NAME`、
  `RESUTIL_GCS_KEY_FILE_PATH` で設定を上書きできます。
- 設定内の相対パスは設定ファイルを基準に解決し、作業ディレクトリは変更しません。
- コメントはUTF-8で200バイトまでです。同名ディレクトリの衝突時は一意な接尾辞を付けます。
- `save_checkpoint()` は無効時・失敗時に `False` を返し、実験を止めません。
  最終アップロードの失敗は例外になり、`resutil push 実験名` で再送できます。
- 同期記録 `results/.resutil-sync.json` により、チェックポイント後の変更も検出します。
  記録のない既存実験は一度再送します。別クライアントによるリモートだけの変更は比較しません。
- コメント変更では依存参照とメタデータも更新します。リモートの依存参照を調べるため、
  リモートアーカイブの読み取りが必要です。
- 安全なログインには、サーバー側も `state` をサインイン画面とコールバックへ
  引き継ぐ必要があります。[互換性の説明](docs/review-fixes.md) とサーバー用パッチを参照してください。
