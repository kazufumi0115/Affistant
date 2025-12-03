from celery import shared_task
from .models import ExtractionRun, Keyword, SearchResult, MediaSite, AffiliateLink
import requests
from bs4 import BeautifulSoup
import time
import random

# 設定ファイルを読み込み
from django.conf import settings
from urllib.parse import urlparse

# ASPドメインリスト (変更なし)
ASP_DOMAINS = {
    "a8.net": "A8",
    "afi-b": "afb",
    "affiliate-b": "afb",
    "valuecommerce": "ValueCommerce",
    "accesstrade": "AccessTrade",
    "rentracks": "Rentracks",
    "felmat": "Felmat",
    "moshimo": "もしも",
    "medipartner": "MediPartner",
    "zucks": "Zucks Affiliate",
    "j-a-net": "JANet",
    "ad-track": "アドトラック",
    "affitown": "affitown",
    "presco": "Presco",
}


def search_google(keyword, max_rank=10):
    """
    Google Custom Search APIを使用して検索を実行する
    """
    api_key = settings.GOOGLE_CSE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID

    if not api_key or not cse_id:
        print("Error: Google API Key or CSE ID is not configured.")
        return None

    url = "https://www.googleapis.com/customsearch/v1"
    all_results = []
    total_hit_count = 0

    # 通し番号用の変数を定義
    current_rank_counter = 1

    # APIは1回で最大10件取得。max_rankまでループで取得する
    for start_index in range(1, max_rank + 1, 10):
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": keyword,
            "num": 10,  # 1リクエストあたりの最大件数
            "start": start_index,
            "gl": "jp",  # 地域: 日本
            "hl": "ja",  # 言語: 日本語
        }

        try:
            print(f"API Request: {keyword} (start={start_index})...")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                print(f"Google API Error: {response.status_code} - {response.text}")
                break

            data = response.json()

            # ヒット件数の取得
            if start_index == 1 and "searchInformation" in data:
                total_results_str = data["searchInformation"].get("totalResults", "0")
                total_hit_count = int(total_results_str)

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                rank = current_rank_counter

                if rank > max_rank:
                    break

                all_results.append(
                    {
                        "rank": rank,
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "snippet": item.get("snippet"),
                    }
                )

                current_rank_counter += 1

            if len(items) < 10:
                break

            if current_rank_counter > max_rank:
                break

            time.sleep(0.5)

        except Exception as e:
            print(f"API Execution Error: {e}")
            break

    return {"results": all_results, "hit_count": total_hit_count}


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

            for asp_key, asp_name in ASP_DOMAINS.items():
                if asp_key in href:
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

        # API検索実行
        search_data = search_google(keyword.text, max_rank=run.max_rank)

        if not search_data or not search_data["results"]:
            print(f"Google search failed or no results for '{keyword.text}'")
            dummy_site, _ = MediaSite.objects.get_or_create(domain="not_found", defaults={"name": "検索結果なし"})

            SearchResult.objects.create(
                run=run,
                keyword=keyword,
                media_site=dummy_site,
                rank=0,
                page_url="",
                title="検索結果なし (API)",
            )
        else:
            if search_data.get("hit_count"):
                keyword.search_volume = search_data["hit_count"]
                keyword.save()

            results_list = search_data["results"]
            print(f"Found {len(results_list)} results via API.")

            for data in results_list:
                parsed_url = urlparse(data["url"])
                domain = parsed_url.netloc

                media_site, _ = MediaSite.objects.get_or_create(domain=domain, defaults={"name": f"{domain}"})

                search_result, created = SearchResult.objects.update_or_create(
                    run=run,
                    keyword=keyword,
                    rank=data["rank"],
                    defaults={
                        "media_site": media_site,
                        "page_url": data["url"],
                        "title": data["title"],
                    },
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
