# 詳細-rye

## 参考

https://zenn.dev/mtkn1/scraps/7c99f088dff2f8

## 概要

uvは、pipに替わるインストールツール + パッケージ管理を簡素化するツールです。
今までパッケージ管理にはpyenv + poetryやpyenv + pipenv、rye + uvなどの組み合わせで構築が必要だったものが、uvだけでPythonインタープリタ含めて管理することが可能です。

## コマンド

### 新規作成

```bash
# 新規作成
uv init <project-name>
# 現在のディレクトリで新規プロジェクトを作成します
uv init
```

### ディレクトリ構造

```
│  .gitignore
│  .python-version
│  pyproject.toml
│  README.md
│
└─src
    └─project_abc
            __init__.py
```

### Pythonバージョン指定

```bash
# Pythonバージョンをピン留めする
# 特定のPythonバージョンを固定します
$ uv python pin 3.12

# インタプリタを一覧する
# 利用可能なPythonインタプリタを表示します
$ uv python list

# インタプリタをインストールする
# 手動でPythonインタプリタをインストールします
$ uv python install 3.12
```

### ライブラリをインストール

```bash
# 依存関係を同期する
uv sync
```

### ライブラリを追加

```bash
# dependenciesに追加 
uv add jinja2
# dev-dependenciesに追加 
uv add --dev jinja2
# dependenciesから削除 
uv remove jinja2 
# 依存関係を指定してスクリプトを実行する
# 必要なパッケージを指定してスクリプトを実行します
uv run --with "requests<3" --with rich main.py
```

### 実行

```bash
uv run python <python file>
```

### オンライン実行

```bash
# Python 製のコマンドラインツールを分離された環境にインストール実行できます
uvx pycowsay hello from uv
```

## コマンドチートシート

| コマンド | 内容 |
| --- | --- |
| uv python install | Pythonのバージョンをインストールする。 |
| uv python list | 利用可能なPythonのバージョンを表示する。 |
| uv python find | インストールされたPythonのバージョンを探す。 |
| uv python pin | 現在のプロジェクトを特定のPythonバージョンに固定する。 |
| uv python uninstall | Pythonのバージョンをアンインストールする。 |
| uv run | スクリプトを実行する。 |
| uv add --script | スクリプトに依存関係を追加する。 |
| uv remove --script | スクリプトから依存関係を削除する。 |
| uv init | 新しいPythonプロジェクトを作成する。 |
| uv add | プロジェクトに依存関係を追加する。 |
| uv remove | プロジェクトから依存関係を削除する。 |
| uv sync | プロジェクトの依存関係を環境と同期する。 |
| uv lock | プロジェクトの依存関係のロックファイルを作成する。 |
| uv tree | プロジェクトの依存関係ツリーを表示する。 |
| uv venv | 新しい仮想環境を作成する。 |
| uv pip install | 環境にパッケージをインストールする。 |
| uv pip show | インストールされたパッケージの詳細を表示する。 |
| uv pip freeze | インストールされたパッケージとそのバージョンをリストする。 |
| uv pip check | 環境に互換性のあるパッケージがあるか確認する。 |
| uv pip list | インストールされたパッケージをリストする。 |
| uv pip uninstall | パッケージをアンインストールする。 |
| uv pip tree | 環境の依存関係ツリーを表示する。 |
| uv pip compile | 要件をロックファイルにコンパイルする。 |
| uv pip sync | ロックファイルと環境を同期する。 |
| uv cache clean | キャッシュエントリを削除する。 |
| uv cache prune | 古いキャッシュエントリを削除する。 |
| uv self update | uvを最新バージョンに更新する。 |