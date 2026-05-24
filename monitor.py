import os
import json
import hashlib
import requests

SEEN_FILE = 'seen_results.json'
MAX_SEEN = 2000  # 保存する最大件数


def search_google(keyword, api_key, cse_id):
    """Google Custom Search APIで予約・発売情報を検索"""
    url = "https://www.googleapis.com/customsearch/v1"
    query = f"{keyword} 予約開始 OR 発売開始 OR 予約受付 OR 販売開始 OR 入荷 OR 発売"
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query,
        'num': 10,
        'sort': 'date',
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get('items', [])
    except Exception as e:
        print(f"検索エラー ({keyword}): {e}")
        return []


def send_ntfy(topic, title, message):
    """ntfy.shでスマホに通知"""
    try:
        r = requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode('utf-8'),
            headers={
                'Title': title,
                'Priority': 'high',
                'Tags': 'shopping,bell',
            },
            timeout=10
        )
        r.raise_for_status()
        print(f"ntfy通知送信成功")
    except Exception as e:
        print(f"ntfy通知エラー: {e}")


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except:
        return set()


def save_seen(seen):
    # 件数が多くなりすぎたら古いものを削除（セットなので順序保証なし→リスト末尾を残す）
    seen_list = list(seen)
    if len(seen_list) > MAX_SEEN:
        seen_list = seen_list[-MAX_SEEN:]
    with open(SEEN_FILE, 'w') as f:
        json.dump(seen_list, f)


def main():
    api_key = os.environ.get('GOOGLE_API_KEY', '')
    cse_id = os.environ.get('GOOGLE_CSE_ID', '')
    ntfy_topic = os.environ.get('NTFY_TOPIC', '')
    keywords_str = os.environ.get('KEYWORDS', '')

    if not all([api_key, cse_id, ntfy_topic, keywords_str]):
        print("環境変数が不足しています（GOOGLE_API_KEY / GOOGLE_CSE_ID / NTFY_TOPIC / KEYWORDS）")
        return

    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    print(f"監視キーワード: {keywords}")

    seen = load_seen()
    new_seen = set(seen)
    found_new = False

    for keyword in keywords:
        print(f"検索中: {keyword}")
        results = search_google(keyword, api_key, cse_id)
        print(f"  → {len(results)} 件ヒット")

        for item in results:
            link = item.get('link', '')
            item_id = hashlib.md5(link.encode()).hexdigest()

            if item_id not in seen:
                found_new = True
                title = item.get('title', '')
                snippet = item.get('snippet', '')[:120]

                message = (
                    f"📝 {snippet}\n"
                    f"🔗 {link}"
                )
                print(f"  新着: {title}")
                send_ntfy(ntfy_topic, f"🔔【{keyword}】{title}", message)
                new_seen.add(item_id)

    save_seen(new_seen)

    if found_new:
        print("新着情報を通知しました")
    else:
        print("新着情報なし")


if __name__ == '__main__':
    main()
