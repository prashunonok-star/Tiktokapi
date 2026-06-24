import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "message": "TikTok Extractor API is running!",
        "usage": "/api/tiktok?url=TIKTOK_URL"
    })

@app.route('/api/tiktok', methods=['GET'])
def extract_tiktok():
    tiktok_url = request.args.get('url')
    
    if not tiktok_url:
        return jsonify({
            "status": "error",
            "message": "Please provide a 'url' query parameter."
        }), 400

    try:
        # Fetching directly from API without yt-dlp
        api_url = "https://www.tikwm.com/api/"
        payload = {'url': tiktok_url}
        
        response = requests.post(api_url, data=payload, timeout=15)
        res_json = response.json()

        if res_json.get('code') == 0:
            data = res_json.get('data', {})
            
            # Format and return the precise metrics including like_count
            result = {
                "status": "success",
                "title": data.get("title"),
                "like_count": data.get("digg_count", 0),      # Exact Like Count
                "comment_count": data.get("comment_count", 0),
                "share_count": data.get("share_count", 0),
                "view_count": data.get("play_count", 0),
                "duration_seconds": data.get("duration", 0),
                "author": {
                    "username": data.get("author", {}).get("unique_id"),
                    "nickname": data.get("author", {}).get("nickname"),
                    "avatar": "https://www.tikwm.com" + data.get("author", {}).get("avatar", "")
                },
                "download_links": {
                    "video_no_watermark": "https://www.tikwm.com" + data.get("play", ""),
                    "video_watermark": "https://www.tikwm.com" + data.get("wmplay", ""),
                    "music_mp3": "https://www.tikwm.com" + data.get("music", "")
                }
            }
            return jsonify(result), 200
        else:
            return jsonify({
                "status": "error",
                "message": res_json.get('msg', 'Could not extract video data. Verify the link.')
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server Error: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Render binds to the PORT environment variable automatically
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)            video_id = match.group(1) if match else None

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
