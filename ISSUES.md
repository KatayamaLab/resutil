# Resutil プロジェクト 問題点レポート

## 1. バグ（重大度: 高）

### 1-1. テストが壊れている — `test_parse_result_dirs`
- **ファイル:** `tests/test_utils.py:9-13`
- テストでは `parse_result_dirs(text)` を文字列1引数で呼んでいるが、実装 (`src/resutil/utils.py:24`) は `parse_result_dirs(argv: list[str], results_dir: str)` で2引数を要求する
- シグネチャ変更時にテストが更新されていない

### 1-2. テストが壊れている — `test_delete_ex_dir`
- **ファイル:** `tests/test_ex_dir.py:19-21`
- テストでは `delete_ex_dir("aaa")` が `ValueError` を発生させることを期待するが、実装 (`src/resutil/ex_dir.py:72-75`) は例外を発生させず `True` を返す

### 1-3. 未定義変数 `config_file_name` の参照
- **ファイル:** `src/resutil/core.py:47`
- `config_file_name` が `core.py` 内で未定義。実行時に `NameError` になる
- `config_file.py` の `CONFIG_FILE_NAME` を使用すべき

### 1-4. バリデーションのエラーメッセージが不正
- **ファイル:** `src/resutil/config_file.py:54-55`
- `backet_name` が無い場合のエラーメッセージが `'base_folder_id'` になっている

### 1-5. `__init__.py` でデコレータファクトリの誤用
- **ファイル:** `src/resutil/__init__.py:4-6`
- `@main` ではなく `@main()` と呼び出す必要がある

### 1-6. GDrive `_find_file_id` が `None` を返しうる
- **ファイル:** `src/resutil/storage/gdrive/gdrive.py:143-151`
- ファイル未発見時に `None` を返すが、呼び出し元で `None` チェックがない

---

## 2. バグ（重大度: 中）

### 2-1. `command_pull` の条件式にデッドコード
- **ファイル:** `src/resutil/cli/cli_main.py:300`
- `args.experiments is None` は `nargs="*"` のため常に `False`

### 2-2. GCS `upload_experiment` でコード重複
- **ファイル:** `src/resutil/storage/gcs/gcs.py:36-41`
- blob 生成が2回実行されている（コピペミス）

### 2-3. ミュータブルデフォルト引数
- **ファイル:** `src/resutil/config_file.py:78-80`
- `dependencies: list[Path] = []` と `uncommited_files: list[str] = []`

### 2-4. `upload_all` の ThreadPoolExecutor が `max_workers=1`
- **ファイル:** `src/resutil/core.py:91`
- マルチスレッドの意味がない。`download_all` は `max_workers=10`

### 2-5. Google Drive API のページネーション未対応
- **ファイル:** `src/resutil/storage/gdrive/gdrive.py:90-108`
- 100件以上の実験がある場合、最初のページ分しか取得できない

### 2-6. 設定読み込み時に `os.chdir()` する副作用
- **ファイル:** `src/resutil/config_file.py:23`

### 2-7. Zip Slip 脆弱性の可能性
- **ファイル:** `src/resutil/core.py:96-98`
- `extractall` にパストラバーサル対策がない

---

## 3. スペルミス・命名の問題

| ファイル | 行 | 誤り | 正しくは |
|---|---|---|---|
| `src/resutil/main.py` | 87 | `Runnning` | `Running` |
| `src/resutil/core.py` | 47 | `Wronge` | `Wrong` |
| `src/resutil/core.py` | 73,76 | `recurcive_uploder` | `recursive_uploader` |
| `src/resutil/core.py` | 113,116 | `recurcive_downloader` | `recursive_downloader` |
| `src/resutil/git.py` | 9 | `repogitory` | `repository` |
| `src/resutil/git.py` | 35,44 | `uncommitd_file_path_list` | `uncommitted_file_path_list` |
| 複数ファイル | — | `uncomited` / `uncommited` | `uncommitted` |
| `src/resutil/storage/gcs/gcs.py`, `src/resutil/cli/cli_main.py` | — | `backet_name` | `bucket_name` |
| `src/resutil/config_file.py` | 17 | `serch` | `search` |
| `src/resutil/config_file.py` | 46 | エラーメッセージに `'local'` | `local` は有効なオプションではない |

---

## 4. 設計・構成の問題

### 4-1. `pytest-mock` が本番依存に含まれている
- **ファイル:** `pyproject.toml:9`
- テスト用パッケージなので `dev-dependencies` にのみ含めるべき

### 4-2. `exist_experiment` が非効率
- **ファイル:** `src/resutil/storage/gcs/gcs.py:71-72`, `src/resutil/storage/gdrive/gdrive.py:140-141`
- 1件の存在チェックのために全実験を毎回リストしている

### 4-3. Storage 基底クラスのインタフェースが不完全
- **ファイル:** `src/resutil/storage/storage.py`
- `remove_experiment`, `change_comment`, `exist_experiment` が未定義
- `abc.ABC` / `abstractmethod` を使用していない

### 4-4. Python バージョン互換性の不整合
- **ファイル:** `pyproject.toml:20`
- `requires-python = ">= 3.8"` だが `list[str]` 等のビルトイン型ジェネリクス (Python 3.9+) を使用
