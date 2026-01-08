# Renderデプロイ設定ガイド

このガイドでは、RenderでTodoリストアプリをデプロイする手順を詳しく説明します。

## 📋 前提条件

- GitHubリポジトリにコードがプッシュされていること
- Renderアカウントがあること（GitHubアカウントでサインアップ可能）

## 🚀 デプロイ手順

### ステップ1: RenderでWebサービスを作成

1. [Render](https://render.com/)にアクセスしてログイン
2. ダッシュボードで「New +」→「Web Service」をクリック
3. GitHubリポジトリを選択（`aiyamagata/toDo_list`）

### ステップ2: 基本設定

以下の設定を入力：

- **Name**: `todo-app`（任意の名前）
- **Region**: `Singapore`（日本に近い地域を選択）
- **Branch**: `main`
- **Root Directory**: （空欄のまま）
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### ステップ3: 環境変数の設定

Renderダッシュボードの「Environment」セクションで、以下の環境変数を追加：

#### 必須の環境変数

1. **SPREADSHEET_ID**
   - 値: あなたのGoogleスプレッドシートID
   - 例: `1Lk7RKfDwE9vYwnzHj701pkCFQd_bozhr36JWzmu0kSU`

2. **SECRET_KEY**
   - 値: ランダムな文字列（セキュリティのため）
   - 生成方法: 以下のコマンドで生成可能
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - または、任意の長いランダムな文字列

3. **PORT**
   - 値: （空欄のまま、Renderが自動設定）

#### オプションの環境変数

- **PYTHON_VERSION**: `3.11`（推奨）

### ステップ4: credentials.jsonの設定

**重要**: `credentials.json`ファイルをRenderにアップロードする必要があります。

#### 方法A: RenderのSecrets機能を使用（推奨）

1. Renderダッシュボードで「Secrets」タブを開く
2. 「Add Secret」をクリック
3. 以下の情報を入力：
   - **Key**: `GOOGLE_CREDENTIALS_JSON`
   - **Value**: `credentials.json`の内容をコピー&ペースト（JSON全体）

4. `app.py`または`sheets_helper.py`を修正して、環境変数から読み込むようにする

#### 方法B: 環境変数として設定

1. `credentials.json`の内容をBase64エンコード
   ```bash
   cat credentials.json | base64
   ```

2. Renderの環境変数に追加：
   - **Key**: `GOOGLE_CREDENTIALS_B64`
   - **Value**: Base64エンコードされた文字列

3. アプリケーション起動時にデコードしてファイルを作成

#### 方法C: シンプルな方法（開発用）

1. `credentials.json`の内容を環境変数として直接設定（非推奨、セキュリティリスクあり）

### ステップ5: デプロイ

1. すべての設定を確認
2. 「Create Web Service」をクリック
3. デプロイが完了するまで待つ（通常3-5分）

## 🔧 トラブルシューティング

### エラー: "gunicorn: command not found"

**解決方法**: `requirements.txt`に`gunicorn==21.2.0`が含まれていることを確認してください。

### エラー: "credentials.json not found"

**解決方法**: 
1. `credentials.json`を環境変数として設定するか
2. コードを修正して環境変数から読み込むようにする

### エラー: "SPREADSHEET_ID not found"

**解決方法**: Renderの環境変数に`SPREADSHEET_ID`が正しく設定されているか確認してください。

### デプロイが成功しない

1. **ログを確認**: Renderダッシュボードの「Logs」タブでエラーを確認
2. **Build Commandを確認**: `pip install -r requirements.txt`が正しいか
3. **Start Commandを確認**: `gunicorn app:app`が正しいか

## 📝 推奨設定

### 本番環境の設定

- **Auto-Deploy**: `Yes`（GitHubにプッシュすると自動デプロイ）
- **Health Check Path**: `/`（オプション）
- **Instance Type**: `Free`（無料プラン）または`Starter`（有料プラン）

### セキュリティのベストプラクティス

1. `SECRET_KEY`は必ずランダムな文字列を使用
2. `credentials.json`はSecrets機能を使用して管理
3. 定期的に認証情報をローテーション

## 🔗 参考リンク

- [Render公式ドキュメント](https://render.com/docs)
- [Gunicorn公式ドキュメント](https://gunicorn.org/)

