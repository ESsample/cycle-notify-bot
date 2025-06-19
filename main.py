from flask import Flask, render_template, request, redirect, url_for
import json
import requests
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# あなたのLINEチャネルアクセストークン
LINE_CHANNEL_ACCESS_TOKEN = '+oEfBnw8K/ZAl5Ywm/VGaVcpW1fCuT+zkZ+IWh6c6XXSQUIE1WMflzbn0Zc2A12jjZzGgquRnQ7sxCIB6aJZntBo2BcBAK9MLXZQNJifu8FQGBkkxsPezDYIxLfBGSl/jeMzDIe63YTshEPfiHEtvwdB04t89/1O/w1cDnyilFU='

# あなたとパートナーのユーザーIDリスト
TO_USER_IDS = [
    'Ue64228332dd7ce110b2ce7e0662c11cc',  # あなたのユーザーID
    'U9d86899eeca7bd99988beb4521bfd24a'  # パートナーの正しいID
]

# あなたのアプリ（登録フォーム）のURL
REGISTER_URL = 'https://198cf6e1-ba95-46df-aaf5-dc8dcadb6e11-00-2vnx0xnpao9i7.pike.replit.dev/'

# データファイル
DATA_FILE = 'data.json'


def send_line_message(message):
    """
    指定した全ユーザーにLINEメッセージを送信する
    """
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    for user_id in TO_USER_IDS:
        body = {'to': user_id, 'messages': [{'type': 'text', 'text': message}]}
        response = requests.post(url, headers=headers, json=body)
        print(f"LINE通知ステータス({user_id}): {response.status_code}")


def save_start_date(start_date):
    """
    💣開始日を保存し、古いデータ（6ヶ月より前）を自動で削除する
    """
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"start_dates": []}

    # 新しい開始日を追加
    data["start_dates"].append(start_date)

    # 6ヶ月以内の記録だけを残す
    six_months_ago = datetime.today().date() - timedelta(days=183)
    filtered_dates = []
    for date_str in data["start_dates"]:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj >= six_months_ago:
            filtered_dates.append(date_str)

    data["start_dates"] = filtered_dates

    # 保存
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def calculate_next_start_date():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    start_dates = data.get("start_dates", [])
    if len(start_dates) < 2:
        return None

    start_dates = [
        datetime.strptime(d, '%Y-%m-%d').date() for d in start_dates
    ]
    cycles = [(start_dates[i] - start_dates[i - 1]).days
              for i in range(1, len(start_dates))]
    average_cycle = sum(cycles) / len(cycles)
    next_date = start_dates[-1] + timedelta(days=round(average_cycle))
    return next_date


def check_and_notify():
    today = datetime.today().date()
    next_start = calculate_next_start_date()
    if next_start and today == next_start - timedelta(days=7):
        message = (f"💣開始予定日まで1週間（予定日: {next_start}）\n"
                   f"開始日を登録\n"
                   f"👉 {REGISTER_URL}")
        send_line_message(message)


@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        start_date = request.form['start_date']
        save_start_date(start_date)
        send_line_message(f"💣が始まりました！（開始日: {start_date}）")
        return redirect(url_for('success'))
    return render_template('register.html')


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    ユーザーIDを取得するためのWebhookエンドポイント
    """
    body = request.get_json()
    print("📨 Webhook受信:", json.dumps(body, indent=2, ensure_ascii=False))
    try:
        user_id = body['events'][0]['source']['userId']
        print(f"✅ あなたのユーザーID: {user_id}")
    except Exception as e:
        print(f"❌ ユーザーID取得失敗: {e}")
    return 'OK', 200


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_notify, 'cron', hour=0, minute=0)
    scheduler.start()

    check_and_notify()  # ★テスト用！即通知を送る！
    
    app.run(host='0.0.0.0', port=8080, debug=True)
