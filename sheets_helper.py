"""
Google Sheets APIを使用してTodoデータを管理するヘルパー関数
"""
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトルートのパスを取得
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# 環境変数を読み込む（明示的にパスを指定）
load_dotenv(dotenv_path=ENV_FILE)

# キャッシュ用のグローバル変数
_todos_cache = None
_cache_timestamp = None
CACHE_DURATION = timedelta(seconds=10)  # キャッシュの有効期限（10秒）

# クライアントキャッシュ
_sheets_client = None
_spreadsheet_cache = None
_worksheet_cache = None

# Google Sheets APIのスコープ
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheets_client():
    """
    Google Sheets APIクライアントを取得する（キャッシュ機能付き）
    
    Returns:
        gspread.Client: Google Sheetsクライアント
    """
    global _sheets_client
    
    if _sheets_client is None:
        # credentials.jsonから認証情報を読み込む
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=SCOPE
        )
        _sheets_client = gspread.authorize(creds)
    
    return _sheets_client

def get_or_create_spreadsheet():
    """
    スプレッドシートを取得または作成する（キャッシュ機能付き）
    
    Returns:
        tuple: (spreadsheet, worksheet) のタプル
    
    Raises:
        Exception: スプレッドシートが見つからない、またはストレージ容量超過の場合
    """
    global _spreadsheet_cache, _worksheet_cache
    
    # キャッシュがあれば使用
    if _spreadsheet_cache is not None and _worksheet_cache is not None:
        return _spreadsheet_cache, _worksheet_cache
    
    client = get_sheets_client()
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    
    # デバッグ情報: .envファイルの存在確認
    env_exists = ENV_FILE.exists()
    
    if not spreadsheet_id:
        # より詳細なエラーメッセージ
        if not env_exists:
            error_msg = (
                "エラー: .envファイルが見つかりません。\n\n"
                "以下の手順で設定してください：\n"
                "1. プロジェクトルート（app.pyと同じフォルダ）に.envファイルを作成\n"
                "2. 以下の内容を記述：\n"
                "   SPREADSHEET_ID=your_spreadsheet_id_here\n"
                "   SECRET_KEY=your-secret-key\n"
                "   PORT=5001\n"
                "3. your_spreadsheet_id_hereを実際のスプレッドシートIDに置き換える\n"
                "4. アプリケーションを再起動"
            )
        else:
            error_msg = (
                "エラー: SPREADSHEET_IDが設定されていません。\n\n"
                ".envファイルは存在しますが、SPREADSHEET_IDが設定されていないか、空の値です。\n\n"
                "以下の手順で設定してください：\n"
                "1. Googleスプレッドシートを手動で作成\n"
                "2. スプレッドシートのURLからIDを取得（URLの/d/と/edit/の間の文字列）\n"
                "   例: https://docs.google.com/spreadsheets/d/【ここがID】/edit\n"
                "3. .envファイルを開き、以下の行を追加または修正：\n"
                "   SPREADSHEET_ID=取得したID\n"
                "   （注意: 等号の前後にスペースを入れないでください）\n"
                "4. スプレッドシートをサービスアカウント（credentials.json内のclient_email）と共有\n"
                "5. アプリケーションを再起動"
            )
        raise Exception(error_msg)
    
    # 既存のスプレッドシートを開く
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = (
            f"エラー: スプレッドシートID '{spreadsheet_id}' が見つかりません。\n"
            "以下の点を確認してください：\n"
            "1. .envファイルのSPREADSHEET_IDが正しいか\n"
            "2. スプレッドシートがサービスアカウント（credentials.json内のclient_email）と共有されているか"
        )
        raise Exception(error_msg)
    except Exception as e:
        # その他のエラー（権限エラーなど）
        error_msg = f"スプレッドシートへのアクセスに失敗しました: {str(e)}"
        raise Exception(error_msg)
    
    # ワークシートを取得または作成
    try:
        worksheet = spreadsheet.worksheet("Todos")
    except gspread.exceptions.WorksheetNotFound:
        # ワークシートが存在しない場合は新規作成
        worksheet = spreadsheet.add_worksheet(title="Todos", rows=1000, cols=10)
        # ヘッダー行を追加
        worksheet.append_row(["ID", "タイトル", "内容", "期日", "作成日時"])
    
    # ヘッダー行が存在するか確認（空のワークシートの場合はエラーを防ぐ）
    try:
        header_row = worksheet.row_values(1)
        if not header_row or len(header_row) == 0:
            # 完全に空の場合はヘッダーを追加（重要度・ステータス列を含む）
            worksheet.update("A1:G1", [["ID", "タイトル", "内容", "期日", "重要度", "作成日時", "ステータス"]])
        elif header_row[0] != "ID" or len(header_row) < 7:
            # ヘッダーが正しくない場合、または重要度・ステータス列がない場合は修正
            if len(header_row) < 7:
                # 重要度・ステータス列を追加
                if len(header_row) < 5:
                    # 重要度列もステータス列もない
                    worksheet.update("A1:G1", [["ID", "タイトル", "内容", "期日", "重要度", "作成日時", "ステータス"]])
                elif len(header_row) < 6:
                    # 重要度列がない
                    worksheet.update("A1:G1", [["ID", "タイトル", "内容", "期日", "重要度", "作成日時", "ステータス"]])
                else:
                    # ステータス列だけ追加
                    worksheet.update("G1", [["ステータス"]])
                    if len(header_row) < 5 or header_row[4] != "重要度":
                        worksheet.update("E1", [["重要度"]])
            else:
                # 既存のヘッダーを確認
                if header_row[0] != "ID":
                    worksheet.update("A1:G1", [["ID", "タイトル", "内容", "期日", "重要度", "作成日時", "ステータス"]])
                else:
                    # 重要度列とステータス列を確認
                    if len(header_row) < 5 or header_row[4] != "重要度":
                        worksheet.update("E1", [["重要度"]])
                    if len(header_row) < 7 or header_row[6] != "ステータス":
                        worksheet.update("G1", [["ステータス"]])
    except (IndexError, gspread.exceptions.APIError):
        # エラーが発生した場合はヘッダーを設定（重要度・ステータス列を含む）
        try:
            worksheet.update("A1:G1", [["ID", "タイトル", "内容", "期日", "重要度", "作成日時", "ステータス"]])
        except:
            # 既にヘッダーがある場合は重要度・ステータス列だけ追加
            try:
                worksheet.update("E1", [["重要度"]])
            except:
                pass
            try:
                worksheet.update("G1", [["ステータス"]])
            except:
                pass
    
    # キャッシュに保存
    _spreadsheet_cache = spreadsheet
    _worksheet_cache = worksheet
    
    return spreadsheet, worksheet

def clear_cache():
    """
    キャッシュをクリアする（データ更新時に呼び出す）
    """
    global _todos_cache, _cache_timestamp, _spreadsheet_cache, _worksheet_cache
    _todos_cache = None
    _cache_timestamp = None
    _spreadsheet_cache = None
    _worksheet_cache = None

def get_all_todos():
    """
    すべてのTodoを取得する（キャッシュ機能付き）
    
    Returns:
        list: Todoのリスト（各Todoは辞書形式）
    """
    global _todos_cache, _cache_timestamp
    
    # キャッシュが有効かチェック
    now = datetime.now()
    if _todos_cache is not None and _cache_timestamp is not None:
        if now - _cache_timestamp < CACHE_DURATION:
            # キャッシュが有効な場合はキャッシュを返す
            return _todos_cache.copy()  # コピーを返して元のキャッシュを保護
    
    # キャッシュが無効または存在しない場合は取得
    _, worksheet = get_or_create_spreadsheet()
    
    try:
        # すべてのレコードを取得（ヘッダー行を含む）
        all_values = worksheet.get_all_values()
        
        # 空のワークシートの場合は空のリストを返す
        if not all_values or len(all_values) <= 1:
            return []
        
        todos = []
        # 2行目から開始（1行目はヘッダー）
        for i, row in enumerate(all_values[1:], start=2):
            # 行が空またはIDが空の場合はスキップ
            if not row or len(row) == 0 or not row[0]:
                continue
            
            # データが不足している場合はデフォルト値を使用
            todo_id = row[0] if len(row) > 0 and row[0] else ""
            title = row[1] if len(row) > 1 else ""
            content = row[2] if len(row) > 2 else ""
            due_date = row[3] if len(row) > 3 else ""
            priority = row[4] if len(row) > 4 else "中"  # 重要度（デフォルト: 中）
            created_at = row[5] if len(row) > 5 else ""
            status = row[6] if len(row) > 6 else ""  # ステータス列
            
            todos.append({
                "id": todo_id,
                "row": i,  # 行番号を保存（編集・削除時に使用）
                "title": title,
                "content": content,
                "due_date": due_date,
                "priority": priority,
                "created_at": created_at,
                "status": status
            })
        
        # キャッシュに保存
        _todos_cache = todos
        _cache_timestamp = now
        
        return todos
    except (IndexError, gspread.exceptions.APIError) as e:
        # エラーが発生した場合は空のリストを返す
        print(f"警告: Todoの取得中にエラーが発生しました: {str(e)}")
        return []

def add_todo(title, content, due_date, priority="中"):
    """
    新しいTodoを追加する
    
    Args:
        title (str): タイトル
        content (str): 内容
        due_date (str): 期日
        priority (str): 重要度（高/中/低、デフォルト: 中）
    
    Returns:
        dict: 追加されたTodoの情報
    """
    _, worksheet = get_or_create_spreadsheet()
    
    # 新しいIDを生成（既存の最大ID + 1）
    todos = get_all_todos_filtered(status_filter="all")
    if todos:
        max_id = max(int(todo["id"]) for todo in todos if todo["id"].isdigit())
        new_id = str(max_id + 1)
    else:
        new_id = "1"
    
    # 現在の日時を取得
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 新しい行を追加（重要度・ステータス列を含む）
    row = [new_id, title, content, due_date, priority, created_at, ""]
    worksheet.append_row(row)
    
    # キャッシュをクリア（データが更新されたため）
    clear_cache()
    
    return {
        "id": new_id,
        "title": title,
        "content": content,
        "due_date": due_date,
        "priority": priority,
        "created_at": created_at
    }

def update_todo(row, title, content, due_date, priority="中"):
    """
    Todoを更新する
    
    Args:
        row (int): 更新する行番号
        title (str): タイトル
        content (str): 内容
        due_date (str): 期日
        priority (str): 重要度（高/中/低、デフォルト: 中）
    """
    _, worksheet = get_or_create_spreadsheet()
    
    # 行を更新（IDと作成日時は変更しない）
    worksheet.update(f"B{row}:E{row}", [[title, content, due_date, priority]])
    
    # キャッシュをクリア（データが更新されたため）
    clear_cache()

def delete_todo(row):
    """
    Todoを削除する
    
    Args:
        row (int): 削除する行番号
    """
    _, worksheet = get_or_create_spreadsheet()
    worksheet.delete_rows(row)
    
    # キャッシュをクリア（データが更新されたため）
    clear_cache()

def complete_todo(row):
    """
    Todoを完了にする
    
    Args:
        row (int): 完了にする行番号
    """
    _, worksheet = get_or_create_spreadsheet()
    # ステータス列（G列）を「完了」に更新
    worksheet.update(f"G{row}", [["完了"]])
    
    # キャッシュをクリア（データが更新されたため）
    clear_cache()

def get_all_todos_filtered(status_filter=None):
    """
    ステータスでフィルタリングしたTodoを取得する
    
    Args:
        status_filter (str, optional): フィルタリングするステータス（None=未完了のみ, "完了"=完了のみ, "all"=すべて）
    
    Returns:
        list: Todoのリスト（各Todoは辞書形式）
    """
    todos = get_all_todos()
    
    if status_filter is None:
        # デフォルト: 未完了のタスクのみ
        return [todo for todo in todos if not todo.get("status") or todo.get("status") != "完了"]
    elif status_filter == "完了":
        # 完了したタスクのみ
        return [todo for todo in todos if todo.get("status") == "完了"]
    else:
        # すべてのタスク
        return todos

