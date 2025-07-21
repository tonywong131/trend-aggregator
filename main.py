import os

if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in os.environ:
    json_content = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
    with open("trend-aggregator-cloud-natural-language.json", "w", encoding="utf-8") as f:
        f.write(json_content)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "trend-aggregator-cloud-natural-language.json"

from dotenv import load_dotenv
import requests
import praw
from google.cloud import language_v1


# 讀 .env
load_dotenv()

# ========== Reddit 熱門 ==========
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)

print("\nReddit 熱門新聞標題：")
try:
    subreddit = reddit.subreddit("news")
    for post in subreddit.hot(limit=5):
        print("🔥", post.title)
except Exception as e:
    print("Reddit error:", e)

# ========== Hacker News 熱門 ==========
print("\nHacker News 熱門標題：")
try:
    top_stories = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
    for story_id in top_stories[:5]:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        story = requests.get(url).json()
        print("🚀", story.get("title"))
except Exception as e:
    print("Hacker News error:", e)

# ========== YouTube Trending ==========
print("\nYouTube Trending 熱門影片：")
youtube_api_key = os.getenv("YOUTUBE_API_KEY")
if youtube_api_key:
    try:
        url = (
            "https://www.googleapis.com/youtube/v3/videos"
            "?part=snippet&chart=mostPopular&regionCode=HK&maxResults=5"
            f"&key={youtube_api_key}"
        )
        res = requests.get(url)
        data = res.json()
        if "items" in data:
            for video in data["items"]:
                title = video["snippet"]["title"]
                channel = video["snippet"]["channelTitle"]
                print(f"▶️ {title}（by {channel}）")
        else:
            print("⚠️ YouTube API error:", data)
    except Exception as e:
        print("YouTube error:", e)
else:
    print("YouTube API key not found.")

# ========== Google Custom Search ==========
print("\nGoogle Custom Search 熱門結果：")
google_cse_api_key = os.getenv("GOOGLE_CSE_API_KEY")
google_cse_id = os.getenv("GOOGLE_CSE_ID")
if google_cse_api_key and google_cse_id:
    try:
        query = "AI news"
        url = (
            "https://www.googleapis.com/customsearch/v1"
            f"?key={google_cse_api_key}"
            f"&cx={google_cse_id}"
            f"&q={query}"
            "&num=5"
        )
        res = requests.get(url)
        data = res.json()
        if "items" in data:
            for item in data["items"]:
                print("🔎", item["title"], "-", item["link"])
        else:
            print("⚠️ Google Custom Search API error:", data)
    except Exception as e:
        print("Google Custom Search error:", e)
else:
    print("Custom Search API key or CSE ID not found.")


print("\nGoogle NLP 全功能測試（情緒、實體、分類）：")
try:
    text = """
    OpenAI、Google、微軟和蘋果在 2025 年進一步加大對人工智能技術的投資，推動了 AI 行業全球爆發。
    中國及美國各大科技企業紛紛推出新一代 AI 語言模型及自動駕駛產品，促使全球市場競爭加劇。
    """
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)

    # 情緒分析
    sentiment_response = client.analyze_sentiment(document=document)
    score = sentiment_response.document_sentiment.score
    magnitude = sentiment_response.document_sentiment.magnitude
    print(f"【情緒分析】分數: {score}，強度: {magnitude}")

    # 實體分析
    entity_response = client.analyze_entities(document=document)
    print("【實體分析】")
    for entity in entity_response.entities:
        print("  -", entity.name, f"(類型: {language_v1.Entity.Type(entity.type_).name})")

    # 內容分類
    try:
        classify_response = client.classify_text(document=document)
        print("【分類】")
        for category in classify_response.categories:
            print("  -", category.name, f"(置信度: {category.confidence})")
    except Exception as ce:
        print("【分類】無法分類（字數太短或內容不足）")

except Exception as e:
    print("Google NLP error:", e)
