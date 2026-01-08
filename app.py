"""
Todoリストアプリケーションのメインファイル
Flaskを使用してWebアプリケーションを構築
"""
from flask import Flask, render_template, request, redirect, url_for, flash
from sheets_helper import get_all_todos_filtered, add_todo, update_todo, delete_todo, complete_todo
import os
from dotenv import load_dotenv
from pathlib import Path

# プロジェクトルートのパスを取得
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# 環境変数を読み込む（明示的にパスを指定）
load_dotenv(dotenv_path=ENV_FILE)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")  # セッション管理用の秘密鍵

@app.route("/")
def index():
    """
    トップページ：Todo一覧を表示（フィルタリング・ソート機能付き）
    """
    try:
        from datetime import datetime, timedelta
        
        # フィルタリングパラメータを取得
        status_filter = request.args.get("status", "未完了")  # デフォルト: 未完了
        priority_filter = request.args.get("priority", "すべて")  # デフォルト: すべて
        due_date_filter = request.args.get("due_date", "すべて")  # デフォルト: すべて
        sort_by = request.args.get("sort", "priority")  # デフォルト: 重要度順
        
        # ステータスでフィルタリング
        if status_filter == "完了":
            todos = get_all_todos_filtered(status_filter="完了")
        elif status_filter == "すべて":
            todos = get_all_todos_filtered(status_filter="all")
        else:  # 未完了
            todos = get_all_todos_filtered(status_filter=None)
        
        # 重要度でフィルタリング
        if priority_filter != "すべて":
            todos = [todo for todo in todos if todo.get("priority") == priority_filter]
        
        # 期日でフィルタリング
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        week_later = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        month_later = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        
        if due_date_filter == "今日":
            todos = [todo for todo in todos if todo.get("due_date") == today_str]
        elif due_date_filter == "今週":
            todos = [todo for todo in todos if todo.get("due_date") and today_str <= todo.get("due_date") <= week_later]
        elif due_date_filter == "今月":
            todos = [todo for todo in todos if todo.get("due_date") and today_str <= todo.get("due_date") <= month_later]
        elif due_date_filter == "期限切れ":
            todos = [todo for todo in todos if todo.get("due_date") and todo.get("due_date") < today_str]
        elif due_date_filter == "期日未設定":
            todos = [todo for todo in todos if not todo.get("due_date")]
        # "すべて"の場合はフィルタリングしない
        
        # ソート処理
        priority_order = {"高": 3, "中": 2, "低": 1}
        
        if sort_by == "priority":
            # 重要度順: 高 > 中 > 低
            todos.sort(key=lambda x: (priority_order.get(x.get("priority", "中"), 2), x.get("due_date", "")), reverse=True)
        elif sort_by == "due_date":
            # 期日順: 早い順
            todos.sort(key=lambda x: (x.get("due_date") or "9999-12-31", priority_order.get(x.get("priority", "中"), 2)), reverse=False)
        
        # 完了したTodoは取り消し線のスタイルを適用するため、完了状態をテンプレートに渡す
        return render_template("index.html", 
                             todos=todos, 
                             sort_by=sort_by,
                             status_filter=status_filter,
                             priority_filter=priority_filter,
                             due_date_filter=due_date_filter)
    except Exception as e:
        error_message = str(e)
        # エラーメッセージをより読みやすくする
        if "storageQuotaExceeded" in error_message or "storage quota" in error_message.lower():
            error_message = (
                "Google Driveのストレージ容量が超過しています。\n"
                "既存のスプレッドシートを使用するか、Driveの容量を解放してください。\n\n"
                "既存のスプレッドシートを使用する手順：\n"
                "1. Googleスプレッドシートを手動で作成\n"
                "2. スプレッドシートのURLからIDを取得（URLの/d/と/edit/の間の文字列）\n"
                "3. .envファイルに SPREADSHEET_ID=取得したID を設定\n"
                "4. スプレッドシートをサービスアカウントと共有"
            )
        flash(error_message, "error")
        return render_template("index.html", todos=[])

@app.route("/add", methods=["GET", "POST"])
def add():
    """
    新しいTodoを追加するページ
    """
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        due_date = request.form.get("due_date", "").strip()
        priority = request.form.get("priority", "中").strip()
        
        # バリデーション
        if not title:
            flash("タイトルは必須です。", "error")
            return render_template("add.html")
        
        try:
            add_todo(title, content, due_date, priority)
            flash("Todoを追加しました！", "success")
            return redirect(url_for("index"))
        except Exception as e:
            error_message = str(e)
            if "storageQuotaExceeded" in error_message or "storage quota" in error_message.lower():
                error_message = (
                    "Google Driveのストレージ容量が超過しています。\n"
                    "既存のスプレッドシートを使用するか、Driveの容量を解放してください。"
                )
            flash(error_message, "error")
            return render_template("add.html")
    
    return render_template("add.html")

@app.route("/edit/<int:row>", methods=["GET", "POST"])
def edit(row):
    """
    Todoを編集するページ
    """
    todos = get_all_todos_filtered(status_filter="all")  # すべてのタスクから検索
    todo = None
    
    # 該当するTodoを検索
    for t in todos:
        if t["row"] == row:
            todo = t
            break
    
    if not todo:
        flash("Todoが見つかりませんでした。", "error")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        due_date = request.form.get("due_date", "").strip()
        priority = request.form.get("priority", "中").strip()
        
        # バリデーション
        if not title:
            flash("タイトルは必須です。", "error")
            return render_template("edit.html", todo=todo)
        
        try:
            update_todo(row, title, content, due_date, priority)
            flash("Todoを更新しました！", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"エラーが発生しました: {str(e)}", "error")
            return render_template("edit.html", todo=todo)
    
    return render_template("edit.html", todo=todo)

@app.route("/delete/<int:row>", methods=["POST"])
def delete(row):
    """
    Todoを削除する
    """
    try:
        delete_todo(row)
        flash("Todoを削除しました！", "success")
    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", "error")
    
    return redirect(url_for("index"))

@app.route("/complete/<int:row>", methods=["POST"])
def complete(row):
    """
    Todoを完了にする
    """
    try:
        complete_todo(row)
        flash("Todoを完了にしました！", "success")
        return redirect(url_for("archive"))
    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/archive")
def archive():
    """
    アーカイブページ：完了したTodo一覧を表示
    """
    try:
        completed_todos = get_all_todos_filtered(status_filter="完了")  # 完了のみ
        return render_template("archive.html", todos=completed_todos)
    except Exception as e:
        flash(f"エラーが発生しました: {str(e)}", "error")
        return render_template("archive.html", todos=[])

if __name__ == "__main__":
    # 開発サーバーを起動
    # ポート5000が使用されている場合は、環境変数PORTで指定するか、デフォルトで5001を使用
    port = int(os.getenv("PORT", 5001))
    print(f"\nサーバーを起動しています...")
    print(f"ブラウザで http://localhost:{port} にアクセスしてください\n")
    app.run(debug=True, host="0.0.0.0", port=port)

