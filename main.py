from supabase import create_client
import os
from dotenv import load_dotenv
import requests
import praw
from datetime import datetime, timezone

# ---------- 設定 Platforms & Categories（用你現有Supabase UUID） ----------
PLATFORMS = {
    "Product Hunt": "1702afc5-9c21-47e8-9ca3-d7f1ae2a61e7",
    "YouTube": "6ef10c55-2825-4458-9f64-5c3899bc3023",
    "Hacker News": "b73cdd80-e499-478f-9a7a-d3eedfb0847a",
    "Reddit": "cc4fab21-1725-4ebd-b9f2-e0a326c8d099",
    "Google Custom Search": "f4d7b076-70be-4157-bf57-a841dbedd44b"
}
CATEGORIES = {
    "AI": "15926262-9bb5-40b8-b572-e8dfe3553f0d",
    "Tech": "4136b324-1f92-467a-8bcc-7f01926e2b6b",
    "Entertainment": "503f42bc-4fc9-49b1-9d86-a3e16e13a59b",
    "Finance": "b35e3978-8e24-4e0c-b427-ae732eacc560",
    "Other": "e104efaf-7ed4-4cb9-84a6-b59eb3d3ec21"
}

# ---------- 連接Supabase ----------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_hot_trend(data):
    try:
        supabase.table("hot_trends").insert(data).execute()
        print("✅ 成功插入：", data["title"])
    except Exception as e:
        print("❌ 插入失敗：", data["title"], "| Error:", e)

now_utc = datetime.now(timezone.utc).isoformat()

# ---------- Reddit 熱門 ----------
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)
for post in reddit.subreddit("news").hot(limit=3):
    data = {
        "title": post.title,
        "description": post.selftext,
        "url": f"https://reddit.com{post.permalink}",
        "platform_id": PLATFORMS["Reddit"],
        "category_id": CATEGORIES["Other"],
        "language": "en",
        "region": "US",
        "posted_at": datetime.fromtimestamp(post.created_utc, timezone.utc).isoformat(),
        "fetched_at": now_utc,
        "popularity": post.score,
        "sentiment_score": None,
        "entities": None,
        "topics": None,
    }
    insert_hot_trend(data)

# ---------- Hacker News 熱門 ----------
top_stories = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
for story_id in top_stories[:3]:
    url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    story = requests.get(url).json()
    data = {
        "title": story.get("title"),
        "description": "",
        "url": story.get("url"),
        "platform_id": PLATFORMS["Hacker News"],
        "category_id": CATEGORIES["Tech"],
        "language": "en",
        "region": "US",
        "posted_at": datetime.fromtimestamp(story.get("time"), timezone.utc).isoformat(),
        "fetched_at": now_utc,
        "popularity": story.get("score"),
        "sentiment_score": None,
        "entities": None,
        "topics": None,
    }
    insert_hot_trend(data)

# ---------- YouTube 熱門 ----------
youtube_api_key = os.getenv("YOUTUBE_API_KEY")
url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&chart=mostPopular&regionCode=HK&maxResults=3&key={youtube_api_key}"
res = requests.get(url)
for video in res.json().get("items", []):
    snippet = video["snippet"]
    data = {
        "title": snippet["title"],
        "description": snippet.get("description", ""),
        "url": f"https://youtube.com/watch?v={video['id']}",
        "platform_id": PLATFORMS["YouTube"],
        "category_id": CATEGORIES["Entertainment"],
        "language": snippet.get("defaultLanguage", "zh"),
        "region": "HK",
        "posted_at": snippet.get("publishedAt"),
        "fetched_at": now_utc,
        "popularity": video.get("statistics", {}).get("viewCount"),
        "sentiment_score": None,
        "entities": None,
        "topics": None,
    }
    insert_hot_trend(data)

# ---------- Google Custom Search 熱門 ----------
google_cse_api_key = os.getenv("GOOGLE_CSE_API_KEY")
google_cse_id = os.getenv("GOOGLE_CSE_ID")
url = f"https://www.googleapis.com/customsearch/v1?key={google_cse_api_key}&cx={google_cse_id}&q=AI&num=3"
res = requests.get(url)
for item in res.json().get("items", []):
    data = {
        "title": item["title"],
        "description": item.get("snippet", ""),
        "url": item["link"],
        "platform_id": PLATFORMS["Google Custom Search"],
        "category_id": CATEGORIES["AI"],
        "language": "en",
        "region": "GLOBAL",
        "posted_at": None,
        "fetched_at": now_utc,
        "popularity": None,
        "sentiment_score": None,
        "entities": None,
        "topics": None,
    }
    insert_hot_trend(data)

print("🎉 全部熱門已寫入 supabase hot_trends！")
