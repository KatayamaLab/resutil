# Resutil

## Resutilとは

**Resutil**は、Pythonプロジェクトから得られた実験結果データを管理するためのユーティリティです。コードや入力データなどの依存関係と共に結果データを管理します。データは Google Cloud Storage（または Google Drive）に同期され、チームでの共有とコラボレーションが可能です。

## なぜResutilを選ぶのか？

- **シンプル**：インストールが簡単ですぐにプロジェクトに導入できます。
- **高い再現性**：プログラム、入力データ、実験結果を追跡します。
- **オープンソースかつ無料**：Resutilの今後のリリースに向けた開発に参加できます。

## 特徴

- プログラムの実行終了後に特定のディレクトリに保存された実験データをクラウド（標準は Google Cloud Storage、または Google Drive）に同期します。
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
Input storage_type (gcs/gdrive): gcs
Input key file_path (key.json): key.json
Do you want to add key.json to .gitignore? (Y/n): Y
Input bucket name: resutil
✅ Initialized.
```
バケット名は Cloud Storage のバケット名です。`resutil-conf.yaml`というファイルが作成されます。
フォルダーIDはBoxのフォルダーIDで、Box上でフォルダーを表示しているときのURL（例：https://xxxx.app.box.com/folder/123456789012）の数値部分です。

`resutil-conf.yaml`というファイルが作成されます。

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

ResutilはGoogle Cloud Storage（標準）とGoogle Driveをサポートしています。各サービスに接続するための手順は以下の通りです。

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


## コマンド

### `resutil init`

`resutil init`は、プロジェクトフォルダ内に`resutil-conf.yaml`を作成します。例:

```yaml
project_name: MyProj
results_dir: results/
storage_type: gcs
storage_config:
  backet_name: resutil  # バケット名
  key_file_path: key.json
```

### `resutil push`

`resutil push`コマンドは、クラウドの結果ディレクトリに存在しない実験データをクラウドにアップロードするために使用されます。

`resutil push [exp_name]`は、特定のディレクトリの実験データをクラウドにアップロードします。`exp-config.yaml`に含まれる依存ディレクトリは自動的にアップロードされます。`--no-dependency`オプションを使用すると、自動依存アップロードが制限されます。

`resutil push --all`は、すべての実験データをクラウドにアップロードします。

### `resutil pull`

`resutil pull`コマンドは、ローカルの結果ディレクトリに存在しない特定の実験データをクラウドからダウンロードするために使用されます。

`resutil pull [exp_name]`は、クラウドから実験ディレクトリをダウンロードします。`exp-config.yaml`に含まれる依存ディレクトリは自動的にダウンロードされます。`--no-dependency`オプションを使用すると、自動依存ダウンロードが制限されます。

`resutil pull --all`は、現在ローカルの結果ディレクトリに存在しないすべての実験データをクラウドからダウンロードします。

これは、特に複数の人が同じプロジェクトに取り組み、実験データを更新している場合に、ローカルデータをクラウドに保存されているデータと同期させるのに便利です。

### `resutil add`

`resutil add`コマンドは、コードを実行せずに実験ディレクトリを追加するために使用されます。

以下のように使用できます: `resutil add [コメント] -d [依存関係1] [依存関係2]...`。このコマンドは、"コメント"という名前の実験ディレクトリを追加し、その依存関係を設定します。依存関係は、この実験が依存する他の実験です。

例えば、`exp1`と`exp2`という2つの実験があり、新しい実験がそれらに依存している場合、次のコマンドで新しい実験を追加できます: `resutil add "新しい実験" -d exp1 exp2`。これにより、"新しい実験"という名前の新しい実験ディレクトリが作成され、`exp1`と`exp2`がその依存関係として設定されます。

### `resutil rm`

`resutil rm` コマンドは実験を削除します。次のように使用できます：`resutil rm [-l] [-r] EXPERIMENT1 [EXPERIMENT2]...`。`--local` または `-l` オプションはローカルの実験ディレクトリのみを削除し、`--remote` または `-r` オプションはクラウド上の実験データを削除します。オプションを指定しない場合、両方の実験データを削除します。

### `resutil comment` **実験的機能**

`resutil comment [EXPERIMENT] [COMMENT]` は、タイムスタンプに続いて実験名にコメントを追加または変更します。既存の実験名が存在する場合、ローカルとクラウドの両方の実験名が変更されます。Resutil は異なる実験名を異なる実験として認識するため、これは他のユーザーが既にプルしている同じ実験の名前には影響しないことに注意してください。

## 実行時の引数

Resutilを組み込んだコードを実行する際には以下の２つの引数を取ることができます。

`--reusitl_comment COMMENT` 実行開始時に求められるコメントを指定します。実行時にコメントを求められなくなります。

`--resutil_no_interactive` 非インタラクティブモードにします。実行時にユーザーへ問い合わせをしなくなります。バッチジョブとして実行する場合に利用します。上記の`--reusitl_comment COMMENT`が指定されていない場合には実験ディレクトリにコメントは付与されません。

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


## デプロイ方法

Add v*.*.* tag will automatically deploy to PyPI
