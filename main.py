from pytrends.request import TrendReq
from supabase import create_client, Client
import os

# ---- ✅ 配置 Supabase ----
# 這兩個變數會在 Railway 上填寫，現在不用在程式內寫死
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- ✅ 初始化 Google Trends ----
pytrends = TrendReq(hl='en-US', tz=360)

def fetch_google_trends():
    trending_searches_df = pytrends.trending_searches(pn='united_states')
    trending_keywords = trending_searches_df[0].tolist()
    return trending_keywords

def save_to_supabase(keywords):
    for keyword in keywords:
        data = {
            "keyword": keyword,
            "platform": "Google Trends",
            "lang": "en",
            "category": "Trending",
            "popularity": 100,
            "growth_rate": 0,
            "emotion": "neutral",
            "original_url": "https://trends.google.com/trends/trendingsearches/daily?geo=US",
            "details": {}
        }
        supabase.table("HotTrends").insert(data).execute()

def main():
    keywords = fetch_google_trends()
    save_to_supabase(keywords)
    print(f"✅ 已更新 {len(keywords)} 條 Google Trends 熱點")

if __name__ == "__main__":
    main()
