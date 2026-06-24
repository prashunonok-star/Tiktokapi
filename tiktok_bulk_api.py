from flask import Flask, jsonify, request
import requests
import re
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

app = Flask(__name__)

class TikTokLikeDetector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.tiktok.com/"
        }

    def extract_video_id(self, url: str) -> str:
        patterns = [
            r"tiktok\.com/@[\w.-]+/video/(\d+)",
            r"vm\.tiktok\.com/([A-Za-z0-9]+)",
            r"tiktok\.com/t/([A-Za-z0-9]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_tiktok_data(self, url: str):
        video_id = self.extract_video_id(url)
        if not video_id and "/video/" in url:
            match = re.search(r'/video/(\d+)', url)
            video_id = match.group(1) if match else None

        if not video_id:
            return {"error": "Could not extract TikTok video ID"}

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Try both known TikTok JSON embed patterns
            match = re.search(r'<script id="SIGI_STATE" type="application/json">(.*?)</script>', response.text, re.DOTALL)
            if not match:
                match = re.search(r'({"__UNIVERSAL_DATA_FOR_REHYDRATION__":.*?});\s*</script>', response.text, re.DOTALL)

            if match:
                raw_json = match.group(1)
                if not raw_json.strip().endswith('}'):
                    raw_json += '}'
                json_data = json.loads(raw_json)

                # Navigate nested structure
                item = (json_data.get('ItemModule', {}).get(video_id) or
                        json_data.get('__UNIVERSAL_DATA_FOR_REHYDRATION__', {})
                        .get('default', {}).get('ItemModule', {}).get(video_id))

                if item:
                    stats = item.get('stats', {})
                    author = item.get('author', '')
                    return {
                        "platform": "tiktok",
                        "video_id": video_id,
                        "likes": int(stats.get('diggCount', 0)),
                        "comments": int(stats.get('commentCount', 0)),
                        "shares": int(stats.get('shareCount', 0)),
                        "views": int(stats.get('playCount', 0)),
                        "saves": int(stats.get('collectCount', 0)),
                        "author": author,
                        "fetched_at": datetime.utcnow().isoformat() + "Z"
                    }

            return {"error": "Failed to parse TikTok data. Page structure may have changed."}

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


detector = TikTokLikeDetector()

def _process_url_safe(url: str):
    """Wrapper to add delay and standardize response format"""
    time.sleep(random.uniform(0.5, 1.5))  # Rate-limit protection
    result = detector.get_tiktok_data(url)
    result["url"] = url
    result["success"] = "error" not in result
    return result

# ========================= ROUTES =========================

@app.route('/')
def home():
    return jsonify({
        "message": "TikTok Like Detection API",
        "endpoints": {
            "single": "GET /api/tiktok?url=<tiktok_link>",
            "bulk": "POST /api/tiktok/bulk (JSON: {\"urls\": [...]})"
        }
    })

@app.route('/api/tiktok', methods=['GET'])
def get_tiktok_likes():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    if 'tiktok.com' not in url.lower():
        return jsonify({"error": "Invalid TikTok URL"}), 400

    result = detector.get_tiktok_data(url)
    result["url"] = url
    result["success"] = "error" not in result
    return jsonify(result)

@app.route('/api/tiktok/bulk', methods=['POST'])
def get_tiktok_likes_bulk():
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({"error": "Provide JSON body with 'urls' array"}), 400

    urls = data['urls']
    if not isinstance(urls, list):
        return jsonify({"error": "'urls' must be an array"}), 400

    MAX_URLS = 30
    if len(urls) > MAX_URLS:
        return jsonify({"error": f"Max {MAX_URLS} URLs per request"}), 400

    results = []
    successful = failed = 0

    # Process concurrently with built-in rate limiting
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_url = {executor.submit(_process_url_safe, url): url for url in urls}
        for future in as_completed(future_to_url):
            try:
                res = future.result()
                if res.get("success"):
                    successful += 1
                else:
                    failed += 1
                results.append(res)
            except Exception as e:
                url = future_to_url[future]
                results.append({"url": url, "success": False, "error": str(e)})
                failed += 1

    # Preserve original input order
    url_order = {u: i for i, u in enumerate(urls)}
    results.sort(key=lambda x: url_order.get(x.get("url"), len(urls)))

    return jsonify({
        "success": True,
        "total_requested": len(urls),
        "successful": successful,
        "failed": failed,
        "results": results
    })

if __name__ == '__main__':
    print("🚀 TikTok Bulk Like API running on http://localhost:5000")
    app.run(debug=True, port=5000)