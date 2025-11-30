from celery import shared_task
from .models import ExtractionRun, Keyword, SearchResult, MediaSite, AffiliateLink
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import urlparse, parse_qs, unquote

# ASPドメインリスト
ASP_DOMAINS = {
    "a8.net": "A8.net",
    "valuecommerce.com": "ValueCommerce",
    "accesstrade.net": "AccessTrade",
    "moshimo.com": "Moshimo",
    "rentracks.jp": "Rentracks",
    "felmat.net": "felmat",
    "afb.jp": "afb",
    "linkshare.ne.jp": "LinkShare",
    "amazon.co.jp": "Amazon",
    "rakuten.co.jp": "Rakuten",
    "presco.jp": "Presco",
    "xmax.jp": "XMAX",
}


def get_search_hit_count(soup):
    """
    Google検索結果ページからヒット件数（約xxx件）を抽出する
    セレクタの種類を増やして対応力を強化
    """
    try:
        # パターン1: ID指定
        result_stats = soup.select_one("#result-stats")
        if result_stats:
            text = result_stats.get_text()
            match = re.search(r"([\d,]+)", text)
            if match:
                return int(match.group(1).replace(",", ""))

        # パターン2: 特定のクラスや構造 (Googleの仕様変更対策)
        # 必要に応じて追加
    except Exception:
        pass
    return None


def search_google(keyword, max_rank=10):
    """
    Google検索を実行する
    """
    # ヘッダーをより一般的なブラウザに偽装
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
    }

    search_url = "https://www.google.co.jp/search"
    params = {"q": keyword, "num": max_rank + 20, "hl": "ja", "gl": "jp", "ie": "UTF-8", "oe": "UTF-8"}  # 多めに取得

    try:
        print(f"Connecting to Google for '{keyword}'...")
        time.sleep(random.uniform(5, 10))  # ブロック回避のため長めに待機

        response = requests.get(search_url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            print(f"Google Search Failed: Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        hit_count = get_search_hit_count(soup)
        results = []

        search_items = soup.select("div.g")
        if not search_items:
            search_items = soup.select("div.MjjYud")

        current_rank = 1
        for item in search_items:
            if current_rank > max_rank:
                break

            title_tag = item.select_one("h3")
            if not title_tag:
                continue

            link_tag = title_tag.find_parent("a")
            if link_tag:
                href = link_tag.get("href")

                if not href or not href.startswith("http"):
                    continue
                if "google.com" in href or "google.co.jp" in href:
                    if "/url?q=" in href:
                        parsed = urlparse(href)
                        qs = parse_qs(parsed.query)
                        if "q" in qs:
                            href = qs["q"][0]
                    else:
                        continue

                title = title_tag.get_text(strip=True)

                if any(r["url"] == href for r in results):
                    continue

                results.append({"rank": current_rank, "title": title, "url": href})
                current_rank += 1

        return {"results": results, "hit_count": hit_count}

    except Exception as e:
        print(f"Google Search Error: {e}")
        return None


def search_duckduckgo(keyword, max_rank=10):
    """
    DuckDuckGo検索 (フォールバック)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # html.duckduckgo.com を使用 (JSなしで解析しやすい)
    url = "https://html.duckduckgo.com/html/"
    data = {"q": keyword}

    try:
        print(f"Connecting to DuckDuckGo for '{keyword}'...")
        time.sleep(random.uniform(3, 6))
        response = requests.post(url, data=data, headers=headers, timeout=30)

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # DuckDuckGo HTML版の結果セレクタ
        result_divs = soup.select("div.result")

        current_rank = 1
        for div in result_divs:
            if current_rank > max_rank:
                break

            # 広告クラスの除外
            if "result--ad" in div.get("class", []):
                continue

            link_tag = div.select_one("a.result__a")
            if link_tag:
                href = link_tag.get("href")

                # === 広告URL・トラッキングURLの除外 ===
                if "duckduckgo.com/y.js" in href or "ad_provider" in href:
                    continue

                # URLデコード
                if "/l/?uddg=" in href:
                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)
                    if "uddg" in qs:
                        href = qs["uddg"][0]

                # デコード後もduckduckgoドメインなら除外 (内部リンク等)
                if "duckduckgo.com" in href:
                    continue

                if not href.startswith("http"):
                    continue

                title = link_tag.get_text(strip=True)

                if any(r["url"] == href for r in results):
                    continue

                results.append({"rank": current_rank, "title": title, "url": href})
                current_rank += 1

        return {"results": results, "hit_count": None}
    except Exception as e:
        print(f"DuckDuckGo Search Error: {e}")
        return None


def extract_affiliate_links_from_url(article_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    found_links = []

    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(article_url, headers=headers, timeout=15)  # タイムアウトを少し延長
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href")
            if not href or not href.startswith("http"):
                continue

            for asp_domain, asp_name in ASP_DOMAINS.items():
                if asp_domain in href:
                    product_name = a_tag.get_text(strip=True)
                    if not product_name:
                        img = a_tag.find("img")
                        if img and img.get("alt"):
                            product_name = img.get("alt")

                    product_name = product_name[:100] if product_name else "画像リンク/テキストなし"

                    if not any(link["link_url"] == href for link in found_links):
                        found_links.append({"asp_name": asp_name, "link_url": href, "product_name": product_name})
                    break
        return found_links
    except Exception as e:
        print(f"Scraping Error ({article_url}): {e}")
        return []


@shared_task(bind=True)
def enqueue_extraction_for_keyword(self, run_id, keyword_id):
    try:
        run = ExtractionRun.objects.get(id=run_id)
        keyword = Keyword.objects.get(id=keyword_id)

        if run.status == "pending":
            run.status = "running"
            run.save()

        print(f"Task started: {keyword.text}")

        # 1. Google検索を試行
        search_data = search_google(keyword.text, max_rank=run.max_rank)

        # 2. Google失敗時はDuckDuckGoへフォールバック
        if not search_data or not search_data["results"]:
            print("Google failed/blocked. Retrying with DuckDuckGo...")
            search_data = search_duckduckgo(keyword.text, max_rank=run.max_rank)

        if not search_data or not search_data["results"]:
            print(f"All search attempts failed for '{keyword.text}'")
            dummy_site, _ = MediaSite.objects.get_or_create(domain="not_found", defaults={"name": "検索結果なし"})
            SearchResult.objects.create(
                run=run,
                keyword=keyword,
                media_site=dummy_site,
                rank=0,
                page_url="",
                title="検索結果が見つかりませんでした",
            )
        else:
            # ヒット数があれば保存 (Google検索成功時のみ)
            if search_data.get("hit_count"):
                keyword.search_volume = search_data["hit_count"]
                keyword.save()

            results_list = search_data["results"]
            print(f"Found {len(results_list)} results.")

            for data in results_list:
                parsed_url = urlparse(data["url"])
                domain = parsed_url.netloc

                media_site, _ = MediaSite.objects.get_or_create(domain=domain, defaults={"name": f"{domain} メディア"})

                search_result, created = SearchResult.objects.update_or_create(
                    run=run,
                    keyword=keyword,
                    media_site=media_site,
                    defaults={"rank": data["rank"], "page_url": data["url"], "title": data["title"]},
                )

                # 指定順位まですべてアフィリエイトリンク抽出
                if data["rank"] <= run.max_rank:
                    affiliate_links_data = extract_affiliate_links_from_url(data["url"])
                    AffiliateLink.objects.filter(search_result=search_result).delete()
                    for aff_data in affiliate_links_data:
                        AffiliateLink.objects.create(
                            search_result=search_result,
                            link_url=aff_data["link_url"][:2000],
                            asp_name=aff_data["asp_name"],
                            product_name=aff_data["product_name"],
                        )

        # 完了判定
        total_keywords_count = run.project.keywords.count()
        processed_keywords_count = SearchResult.objects.filter(run=run).values("keyword").distinct().count()

        if processed_keywords_count >= total_keywords_count:
            run.status = "completed"
            run.save()
            print(f"Run {run_id} COMPLETED.")

        return f"Success: {keyword.text} ({len(search_data['results']) if search_data else 0} results)"

    except Exception as e:
        print(f"Task failed: {e}")
        return f"Error: {str(e)}"
