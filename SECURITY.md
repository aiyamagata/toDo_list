# セキュリティガイド

このドキュメントでは、このプロジェクトのセキュリティに関する重要な情報を説明します。

## ⚠️ 重要な注意事項

### 機密情報を含むファイル

以下のファイルは**絶対にGitにコミットしないでください**：

1. **`.env`** - 環境変数ファイル
   - `SPREADSHEET_ID`
   - `SECRET_KEY`
   - `PORT`
   - これらは`.gitignore`に追加済みです

2. **`credentials.json`** - Google API認証情報
   - サービスアカウントの秘密鍵が含まれています
   - これも`.gitignore`に追加済みです

### `.gitignore`の確認

以下のファイルは自動的に除外されています：

```
.env
credentials.json
*.json（credentials.json以外）
__pycache__/
.DS_Store
```

### 環境変数の設定方法

1. `.env.example`をコピーして`.env`を作成
2. 必要な値を設定：
   ```
   SPREADSHEET_ID=your_spreadsheet_id
   SECRET_KEY=your-secret-key
   PORT=5001
   ```

### GitHubにプッシュした後

もし誤って機密情報をコミットしてしまった場合は、以下の手順を実行してください：

1. **すぐに認証情報を無効化**
   - Google Cloud Consoleでサービスアカウントキーを削除
   - 新しいサービスアカウントキーを発行
   - `.env`ファイルの値を更新

2. **GitHubの機密情報を削除**
   - GitHubのSettings > Security > Secretsから削除
   - または、リポジトリを削除して再作成

3. **Git履歴から削除**（上級者向け）
   ```bash
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch .env credentials.json" \
   --prune-empty --tag-name-filter cat -- --all
   ```

### 推奨事項

- `.env`ファイルを共有する場合は、暗号化して共有
- 本番環境では環境変数を直接設定（ファイルではなく）
- 定期的に認証情報をローテーション
- `.env.example`には実際の値を含めない

