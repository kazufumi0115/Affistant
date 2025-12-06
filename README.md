# Affistant Project

このプロジェクトは、Django (Backend) と React (Frontend) を使用したWebアプリケーションです。

## システム構成

* **Backend**: Django, Django REST Framework
* **Frontend**: React (Create React App)
* **Database**: PostgreSQL
* **Cache / Message Broker**: Redis
* **Task Queue**: Celery (Worker & Beat)

## 前提条件とツールのインストール

このプロジェクトを実行するには、以下のツールが必要です。まだインストールされていない場合は、手順に従ってインストールしてください。

### 1. Git のインストール

ソースコードを取得するために使用します。

* **Windows**: [Git for Windows](https://gitforwindows.org/) をダウンロードしてインストールします。
* **macOS**: ターミナルで `git --version` を実行します。インストールされていない場合はプロンプトに従うか、[Homebrew](https://brew.sh/) を使って `brew install git` でインストールします。
* **Linux**: パッケージマネージャを使用します（例: `sudo apt install git`）。

### 2. Docker のインストール

コンテナを実行するためのプラットフォームです。

* **Windows / macOS**:
    [Docker Desktop](https://www.docker.com/products/docker-desktop/) 公式サイトからインストーラーをダウンロードし、実行してください。
    * *注意*: インストール完了後、Docker Desktop アプリケーションを起動しておく必要があります。
* **Linux (Ubuntuなど)**:
    公式ドキュメントに従って Docker Engine をインストールすることを推奨します。
    * [Ubuntuへのインストール手順](https://docs.docker.com/engine/install/ubuntu/)

### 3. Docker Compose の確認

複数のコンテナを定義・実行するためのツールです。

* **Windows / macOS**: Docker Desktop に含まれているため、別途インストールは不要です。
* **Linux**: 最新の Docker CLI (Docker Compose V2) がインストールされていれば `docker compose` コマンドが使えます。
    * 確認コマンド: `docker compose version`

## 開発環境構築手順

### 1. リポジトリのクローン

プロジェクトのリポジトリをローカルにクローンし、ディレクトリに移動します。

```bash
git clone <repository-url>
cd affistant
```

### 2. 環境変数の設定

プロジェクトルートにある `.env_example` ファイルをコピーして、`.env` ファイルを作成します。

```bash
cp .env_example .env
```

作成した `.env` ファイルを開き、必要に応じて環境変数を設定してください。
Google Custom Search APIを使用する場合は、`GOOGLE_CSE_API_KEY` と `GOOGLE_CSE_ID` の設定が必要です。

**主な環境変数:**
* `DEBUG`: デバッグモード (開発時は `1`)
* `SECRET_KEY`: Djangoのシークレットキー
* `DATABASE_URL`: データベース接続情報
* `GOOGLE_CSE_API_KEY`: Google Custom Search API キー
* `GOOGLE_CSE_ID`: Google Custom Search Engine ID

### 3. Docker コンテナのビルドと起動

以下のコマンドを実行して、Dockerイメージのビルドとコンテナの起動を行います。

```bash
docker-compose up -d --build
```

* `-d`: バックグラウンドで実行します。
* `--build`: イメージの再ビルドを強制します（初回や `Dockerfile` 変更時に推奨）。

### 4. アプリケーションへのアクセス

コンテナが正常に起動したら、ブラウザで以下のURLにアクセスして動作を確認してください。

* **Frontend (React)**: [http://localhost:3000](http://localhost:3000)
* **Backend API (Django)**: [http://localhost:8000](http://localhost:8000)

### 5. データベースのマイグレーション

初回起動時やモデル定義を変更した際は、データベースのマイグレーションを実行してテーブルを作成・更新する必要があります。

```bash
docker-compose exec backend python manage.py migrate
```

### 6. 管理ユーザー (Superuser) の作成

Djangoの管理画面 ([http://localhost:8000/admin/](http://localhost:8000/admin/)) にログインするための管理者ユーザーを作成します。

```bash
docker-compose exec backend python manage.py createsuperuser
```

プロンプトに従って、ユーザー名、メールアドレス、パスワードを入力してください。

## テスト手順

### Backend (Django) のテスト

バックエンドの単体テストを実行します。

```bash
# 全てのテストを実行
docker-compose exec backend python manage.py test

# 特定のアプリケーションのみテストを実行 (例: trackingアプリ)
docker-compose exec backend python manage.py test tracking
```

### Frontend (React) のテスト

フロントエンドのテストを実行します。CI環境のように一度だけ実行して終了する場合は、以下のコマンドを使用します。

```bash
docker-compose exec frontend npm test -- --watchAll=false
```

インタラクティブモード（監視モード）で実行したい場合は、以下のようにコンテナに入って実行することを推奨します。

```bash
docker-compose exec frontend sh
npm test
```

## よく使うコマンド

* **コンテナの停止**:
    ```bash
    docker-compose down
    ```
* **ログの確認 (リアルタイム表示)**:
    ```bash
    # 全てのサービス
    docker-compose logs -f

    # 特定のサービス (例: backend)
    docker-compose logs -f backend
    ```
* **Frontendパッケージの追加**:
    ```bash
    docker-compose exec frontend npm install <package-name>
    ```
    ※ インストール後は、必要に応じてイメージをリビルドしてください。

## トラブルシューティング

* **データベースに接続できない場合**:
    コンテナが完全に立ち上がるまで少し時間がかかる場合があります。数秒待ってから再試行するか、`docker-compose logs db` でエラーが出ていないか確認してください。
* **コードの変更が反映されない場合**:
    Frontendの変更が反映されない場合、Dockerのファイル監視ポーリング設定が有効になっているか確認してください (`CHOKIDAR_USEPOLLING=true` が `docker-compose.yml` に設定されています)。
