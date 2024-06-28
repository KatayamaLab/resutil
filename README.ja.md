# Resutil

## Resutilとは

**Resutil**は、Pythonプロジェクトから得られた実験結果データを管理するためのユーティリティです。コードや入力データなどの依存関係と共に結果データを管理します。データはクラウドに同期され、チームでの共有とコラボレーションが可能です。

## なぜResutilを選ぶのか？

- **シンプル**：インストールが簡単ですぐにプロジェクトに導入できます。
- **高い再現性**：プログラム、入力データ、実験結果を追跡します。
- **オープンソースかつ無料**：Resutilの今後のリリースに向けた開発に参加できます。

## 特徴

- プログラムの実行終了後に特定のディレクトリに保存された実験データをクラウド（現在はBoxのみ）に同期します。
- 実験を再現するために必要な情報をYAMLファイルに保存します。
  - 実行コマンド
  - 引数で指定された入力ファイル（resutilで管理しているフォルダ内のファイルのみ）
  - Gitのコミットハッシュ
  - コミットされていないファイル
- アップロードされていない実験データをアップロードできます。
- コマンドを使用してクラウドから実験データをダウンロードできます。

## インストール

ターミナルを開いて以下を実行

```bash
pip install resutil
```

[Box](https://developer.box.com/guides/authentication/jwt/)からJWT（JSON Web Tokens）キーを取得し、`key.json`として保存します。

```JSON
{
  "boxAppSettings": {
    "clientID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "appAuth": {
      "publicKeyID": "xxxxxxxx",
      "privateKey": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n-----END ENCRYPTED PRIVATE KEY-----\n",
      "passphrase": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  },
  "enterpriseID": "796607301"
}
```

resutilを初期化します

```bash
$ cd your-project-root-directory
$ resutil init
Input project name (resutil): MyProj
Input directory name to store results (results): results
Do you want to add .gitignore to results? (Y/n): Y
Input storage_type (box): box
Input key file_path (key.json): key.json
Do you want to add key.json to .gitignore? (Y/n): Y
Input folder id of base dir: 123456789012
✅ Initialized.
```

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

## クラウドストレージ設定方法

ResutilはGoogle Cloud Storage、Google Drive、およびBoxをサポートしています。これらのクラウドサービスに接続するには、以下の設定が必要です。

### Google Cloud Storage

1. **プロジェクトの作成**:
    - まだプロジェクトがない場合は、[Google Cloud Console](https://console.cloud.google.com/)にアクセスして新しいプロジェクトを作成します。
2. **Cloud Storage APIを有効にする**:
    - Google Cloud Consoleの[APIライブラリ](https://console.cloud.google.com/apis/library)に移動します。
    - 「Cloud Storage」を検索し、プロジェクトのAPIを有効にします。
3. **ストレージバケットの作成**:
    - Google Cloud Consoleの[Cloud Storageブラウザ](https://console.cloud.google.com/storage/browser)に移動します。
    - 「バケットを作成」をクリックします。
    - バケットに名前を付け、ストレージクラスを選択し、バケットの場所を設定するプロンプトに従います。
4. **サービスアカウントの作成**:
    - Google Cloud Consoleの[IAMと管理](https://console.cloud.google.com/iam-admin/serviceaccounts)セクションに移動します。
    - 「サービスアカウントを作成」をクリックします。
    - サービスアカウントの名前と説明を入力し、「作成」をクリックします。
5. **サービスアカウントに権限を付与**:
    - サービスアカウントに必要な権限を付与するためのロール「Storageオブジェクトユーザー」を選択します。
    - 「続行」をクリックし、その後「完了」をクリックします。
6. **サービスアカウントのキーを作成してダウンロード**:
    - 先ほど作成したサービスアカウントをクリックします。
    - 「キー」タブに移動します。
    - 「キーを追加」、次に「新しいキーを作成」をクリックします。
    - 「JSON」をキーの種類として選択し、「作成」をクリックします。キーが含まれたファイルがコンピュータにダウンロードされます。

### Google Drive

1. **Google Driveにフォルダを作成**:
    - [Google Drive](https://drive.google.com/)を開きます。
    - 「新規」をクリックし、「フォルダ」を選択します。
    - フォルダに名前を付けて「作成」をクリックします。
2. **フォルダIDを取得**:
    - 作成したフォルダに移動します。
    - フォルダIDは、URLの`folders/`の後に続く部分です。例えば、`https://drive.google.com/drive/folders/1a2b3c4d5e6f`というURLの場合、フォルダIDは`1a2b3c4d5e6f`です。
3. **サービスアカウントの作成**:
    - [Google Cloud Console](https://console.cloud.google.com/)に移動します。
    - プロジェクトを選択するか、新しいプロジェクトを作成します。
    - [IAMと管理](https://console.cloud.google.com/iam-admin/serviceaccounts)セクションに移動します。
    - 「サービスアカウントを作成」をクリックします。
    - サービスアカウントの名前と説明を入力し、「作成」をクリックします。
4. **サービスアカウントのキーを作成してダウンロード**:
    - 先ほど作成したサービスアカウントをクリックします。
    - 「キー」タブに移動します。
    - 「キーを追加」、次に「新しいキーを作成」をクリックします。
    - 「JSON」をキーの種類として選択し、「作成」をクリックします。キーが含まれたファイルがコンピュータにダウンロードされます。
5. **Google Drive APIを有効にする**:
    - Google Cloud Consoleの[APIライブラリ](https://console.cloud.google.com/apis/library)に移動します。
    - 「Google Drive API」を検索し、プロジェクトのAPIを有効にします。
6. **フォルダを共有**:
    - Google Driveで、作成したフォルダを右クリックします。
    - 「共有」を選択します。
    - 「ユーザーやグループと共有」フィールドに、サービスアカウントのメールアドレス（JSONキーにある`client_email`の下にあります）を入力します。
    - サービスアカウントに`編集者`のアクセス権を与えます。
    - 「送信」をクリックします。

### Box

Boxの開発者コンソールからJWT（JSON Web Token）を取得する手順をご案内します。以下の手順に従ってください：

1. **Boxアプリケーションの作成**
    - [開発者コンソール](https://account.box.com/login)にアクセスしてBoxアカウントにログインします。
    - 「アプリの新規作成」をクリックします。
    - アプリに名前を付け、「次へ」をクリックします。
    - 「カスタムアプリ」を選択し、「サーバー認証 (JWTを使用)」を選びます。

2. **アプリケーションの設定**
    - アプリの設定で、「構成」タブに移動します。
    - 「アプリケーションスコープ」では、「Boxに格納されているすべてのファイルとフォルダの読み取り/書き込み」の2つのアクセスレベルを選択します。
    - 下にスクロールして「公開キーの追加と管理」セクションで「公開/秘密キーペアを生成」をクリックします。これにより、アプリのクレデンシャルが含まれた`.json`ファイルがダウンロードされます。

3. **サービスアカウントの作成**
    - 「承認」タブで「サービスアカウントを作成」をクリックします。
    - 指示に従ってサービスアカウントを作成します。このアカウントはアプリの認証に使用されます。

4. **サービスアカウントに権限を付与**
    - 使用したいフォルダに対して、サービスアカウント“AutomationUser_xxxxx@boxdevedition.com”に編集権限を与えます。

## コマンド

### `resutil init`

`resutil init`は、プロジェクトフォルダ内に`resutil-conf.yaml`を作成します。例:

```yaml
project_name: MyProj
results_dir: results/
storage_type: box
storage_config:
  base_folder_id: xxxx
  key_file: key.json
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

## クラウドストレージのディレクトリ構成

```plaintext
BaseDir    # base_dir_idで指定されたベースディレクトリ
├──MyProj  # プロジェクトディレクトリ
│   ├── aakuqj_20240511T174522_ex1  # 実験ディレクトリ
│   │   ├── resutil-exp.yaml       # 実験情報
│   │   └── data.txt               # データ（例）
│   ├── aamxrp_20240606T135747_ex2
│   │   ├── resutil-exp.yaml
│   │   ├── data.txt
│   │   └── uncommited_files       # コミットされていないファイル
│   │       └── main.py
│   ...
│   
├──OtherProj
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
