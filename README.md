# Trend Aggregator 多平台熱點聚合系統

自動收集分析多平台熱點，包括 Reddit、Hacker News、YouTube、Google、Product Hunt 等，並可寫入 Supabase 資料庫，支援語言、地區、分類、情緒等分析。

---

## 功能簡介

- 支援多平台熱點自動抓取（Reddit, Hacker News, YouTube, Google Custom Search...）
- 自動 Google NLP 分析（情緒、實體、分類）
- 熱度計算、增長率、分類、情緒等數據
- 資料寫入 Supabase 雲端資料庫
- 可擴充平台與自訂搜尋條件（地區、語言等）

---

## 安裝及運行方法

### 1. Clone 專案
```bash
git clone https://github.com/tonywong131/trend-aggregator.git
cd trend-aggregator
