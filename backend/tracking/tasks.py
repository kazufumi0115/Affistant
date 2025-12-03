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
    """Google検索結果ページからヒット件数を抽出"""
    try:
        result_stats = soup.select_one("#result-stats")
        if result_stats:
            text = result_stats.get_text()
            match = re.search(r"([\d,]+)", text)
            if match:
                return int(match.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def search_google(keyword, max_rank=10):
    """Google検索を実行"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    search_url = "https://www.google.co.jp/search"
    params = {
        "q": keyword,
        "num": max_rank + 20,  # 余分に取得
        "hl": "ja",
        "gl": "jp",
    }

    try:
        print(f"Connecting to Google for '{keyword}'...")
        time.sleep(random.uniform(5, 10))

        response = requests.get(search_url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            print(f"Google Search Failed: Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        hit_count = get_search_hit_count(soup)
        results = []

        # Google検索結果のセレクタ (div.g または div.MjjYud)
        search_items = []
        main_column = soup.select_one("#search")
        if main_column:
            all_links = main_column.find_all("a")

            current_rank = 1
            for link in all_links:
                if current_rank > max_rank:
                    break

                h3 = link.find("h3")
                if not h3:
                    # 親要素がh3かチェック
                    if link.parent.name == "h3":
                        h3 = link.parent
                    else:
                        continue

                href = link.get("href")

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

                title = h3.get_text(strip=True)

                if any(r["url"] == href for r in results):
                    continue

                results.append({"rank": current_rank, "title": title, "url": href})
                current_rank += 1

        return {"results": results, "hit_count": hit_count}

    except Exception as e:
        print(f"Google Search Error: {e}")
        return None


def extract_affiliate_links_from_url(article_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    found_links = []

    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(article_url, headers=headers, timeout=15)
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

        # Google検索のみ実行
        search_data = search_google(keyword.text, max_rank=run.max_rank)

        if not search_data or not search_data["results"]:
            print(f"Google search failed for '{keyword.text}'")
            dummy_site, _ = MediaSite.objects.get_or_create(domain="not_found", defaults={"name": "検索結果なし"})
            SearchResult.objects.create(
                run=run,
                keyword=keyword,
                media_site=dummy_site,
                rank=0,
                page_url="",
                title="検索結果が見つかりませんでした (Google Blocked)",
            )
        else:
            if search_data.get("hit_count"):
                keyword.search_volume = search_data["hit_count"]
                keyword.save()

            results_list = search_data["results"]
            print(f"Found {len(results_list)} results.")

            for data in results_list:
                parsed_url = urlparse(data["url"])
                domain = parsed_url.netloc

                media_site, _ = MediaSite.objects.get_or_create(domain=domain, defaults={"name": f"{domain}"})

                search_result, created = SearchResult.objects.update_or_create(
                    run=run,
                    keyword=keyword,
                    media_site=media_site,
                    defaults={"rank": data["rank"], "page_url": data["url"], "title": data["title"]},
                )

                # 指定順位までアフィリエイトリンク抽出
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

        return f"Success: {keyword.text}"

    except Exception as e:
        print(f"Task failed: {e}")
        return f"Error: {str(e)}"
