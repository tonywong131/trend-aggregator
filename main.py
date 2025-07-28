import os, base64

# 1. 從環境變數讀 Base64
b64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not b64:
    raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS_B64")

# 2. 解碼並寫到暫存檔
json_path = "/app/trend-aggregator-cloud-natural-language.json"
with open(json_path, "wb") as f:
    f.write(base64.b64decode(b64))

# 3. 告訴 Google SDK 路徑
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path

import sys
import requests
import praw
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timezone
from google.cloud import language_v1

# ======= Platform & Category UUID（請確保已更新到 supabase 最新值）=======
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
    "Other": "請填你Supabase現時Other UUID"  # <== 必須自己貼返Supabase最新值！
}

# ======= 初始化 Supabase、NLP Client =======
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
now_utc = datetime.now(timezone.utc).isoformat()
NLP_CLIENT = language_v1.LanguageServiceClient()
KG_API_KEY = os.getenv("GOOGLE_KG_API_KEY")

def analyze_with_nlp(text):
    try:
        document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
        sentiment = NLP_CLIENT.analyze_sentiment(document=document).document_sentiment
        sentiment_score = sentiment.score
        entities_resp = NLP_CLIENT.analyze_entities(document=document)
        entities = [entity.name for entity in entities_resp.entities]
        try:
            category_resp = NLP_CLIENT.classify_text(document=document)
            topics = [category.name for category in category_resp.categories]
        except:
            topics = []
        return sentiment_score, entities, topics
    except Exception as e:
        print("NLP error:", e)
        return None, [], []

def get_kg_info(keyword):
    try:
        url = f"https://kgsearch.googleapis.com/v1/entities:search?query={keyword}&key={KG_API_KEY}&limit=1"
        res = requests.get(url)
        data = res.json()
        if "itemListElement" in data and data["itemListElement"]:
            entity = data["itemListElement"][0]["result"]
            entity_type = entity.get("@type", [])
            description = entity.get("description", "")
            wiki_url = entity.get("detailedDescription", {}).get("url", "")
            return {"kg_type": entity_type, "kg_desc": description, "kg_wiki": wiki_url}
        else:
            return {}
    except Exception as e:
        print("KG error:", e)
        return {}

def insert_hot_trend(data):
    try:
        supabase.table("hot_trends").insert(data).execute()
        print("✅ 插入：", data["title"])
    except Exception as e:
        print("❌ 插入失敗：", data["title"], "| Error:", e)

# ======= 平台任務 function =======

def run_reddit():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )
    for post in reddit.subreddit("news").hot(limit=50):
        text = (post.title or "") + "\n" + (post.selftext or "")
        sentiment_score, nlp_entities, topics = analyze_with_nlp(text)
        kg = get_kg_info(post.title)
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
            "sentiment_score": sentiment_score,
            "entities": nlp_entities,
            "topics": topics,
            "kg_type": str(kg.get("kg_type")),
            "kg_desc": kg.get("kg_desc"),
            "kg_wiki": kg.get("kg_wiki"),
        }
        insert_hot_trend(data)

def run_hackernews():
    top_stories = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
    for story_id in top_stories[:50]:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        story = requests.get(url).json()
        title = story.get("title", "")
        text = title + "\n" + (story.get("text", "") or "")
        sentiment_score, nlp_entities, topics = analyze_with_nlp(text)
        kg = get_kg_info(title)
        data = {
            "title": title,
            "description": story.get("text", ""),
            "url": story.get("url"),
            "platform_id": PLATFORMS["Hacker News"],
            "category_id": CATEGORIES["Tech"],
            "language": "en",
            "region": "US",
            "posted_at": datetime.fromtimestamp(story.get("time"), timezone.utc).isoformat(),
            "fetched_at": now_utc,
            "popularity": story.get("score"),
            "sentiment_score": sentiment_score,
            "entities": nlp_entities,
            "topics": topics,
            "kg_type": str(kg.get("kg_type")),
            "kg_desc": kg.get("kg_desc"),
            "kg_wiki": kg.get("kg_wiki"),
        }
        insert_hot_trend(data)

def run_youtube():
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    # 每次最多50條
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&chart=mostPopular&regionCode=HK&maxResults=50&key={youtube_api_key}"
    res = requests.get(url)
    for video in res.json().get("items", []):
        snippet = video["snippet"]
        title = snippet["title"]
        description = snippet.get("description", "")
        text = title + "\n" + description
        sentiment_score, nlp_entities, topics = analyze_with_nlp(text)
        kg = get_kg_info(title)
        data = {
            "title": title,
            "description": description,
            "url": f"https://youtube.com/watch?v={video['id']}",
            "platform_id": PLATFORMS["YouTube"],
            "category_id": CATEGORIES["Entertainment"],
            "language": snippet.get("defaultLanguage", "zh"),
            "region": "HK",
            "posted_at": snippet.get("publishedAt"),
            "fetched_at": now_utc,
            "popularity": video.get("statistics", {}).get("viewCount"),
            "sentiment_score": sentiment_score,
            "entities": nlp_entities,
            "topics": topics,
            "kg_type": str(kg.get("kg_type")),
            "kg_desc": kg.get("kg_desc"),
            "kg_wiki": kg.get("kg_wiki"),
        }
        insert_hot_trend(data)

def run_customsearch():
    google_cse_api_key = os.getenv("GOOGLE_CSE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")
    # Google CSE每次最多10條，要分5次 query
    for n in range(5):
        start = n * 10 + 1
        url = f"https://www.googleapis.com/customsearch/v1?key={google_cse_api_key}&cx={google_cse_id}&q=AI&num=10&start={start}"
        res = requests.get(url)
        for item in res.json().get("items", []):
            title = item["title"]
            description = item.get("snippet", "")
            text = title + "\n" + description
            sentiment_score, nlp_entities, topics = analyze_with_nlp(text)
            kg = get_kg_info(title)
            data = {
                "title": title,
                "description": description,
                "url": item["link"],
                "platform_id": PLATFORMS["Google Custom Search"],
                "category_id": CATEGORIES["AI"],
                "language": "en",
                "region": "GLOBAL",
                "posted_at": None,
                "fetched_at": now_utc,
                "popularity": None,
                "sentiment_score": sentiment_score,
                "entities": nlp_entities,
                "topics": topics,
                "kg_type": str(kg.get("kg_type")),
                "kg_desc": kg.get("kg_desc"),
                "kg_wiki": kg.get("kg_wiki"),
            }
            insert_hot_trend(data)

# ======= 執行主流程（支援多平台 flag）=======
if __name__ == "__main__":
    if len(sys.argv) > 1:
        platforms = [arg.lower() for arg in sys.argv[1:]]
    else:
        platforms = ["reddit", "hackernews", "youtube", "customsearch"]

    if "reddit" in platforms:
        run_reddit()
    if "hackernews" in platforms:
        run_hackernews()
    if "youtube" in platforms:
        run_youtube()
    if "customsearch" in platforms:
        run_customsearch()

    print("🎉 熱點已全部寫入 supabase hot_trends（NLP+KnowledgeGraph）！")
