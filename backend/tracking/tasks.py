from celery import shared_task
from .models import ExtractionRun, SearchResult, MediaSite, Keyword
from django.utils import timezone
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


@shared_task(bind=True)
def enqueue_extraction_for_keyword(self, run_id):
    try:
        run = ExtractionRun.objects.get(id=run_id)
        run.status = "running"
        run.started_at = timezone.now()
        run.save()

        keyword = run.keyword
        # --- ここから実装する検索ロジック ---
        # 注意: Google の直接スクレイピングはTOSの問題やブロックがあるため
        # 実運用では SerpAPI 等のサードパーティを使うか、プロキシ/レート制御 を行うこと。
        query = keyword.text
        top_n = keyword.top_n

        # Example: use SERP API (pseudocode)
        # response = call_serp_api(query, top_n, region=keyword.region)
        # run.raw_response = response
        # for idx, item in enumerate(response['organic_results'], start=1):
        #     domain = urlparse(item['link']).netloc
        #     SearchResult.objects.create(
        #         run=run, keyword=keyword, position=idx,
        #         is_ad=False, url=item['link'], domain=domain,
        #         title=item.get('title'), snippet=item.get('snippet')
        #     )
        #
        # For MVP demo, we can fallback to a VERY simple scraping or mock.

        run.status = "success"
        run.finished_at = timezone.now()
        run.save()
    except Exception as e:
        run.status = "failed"
        run.note = str(e)
        run.finished_at = timezone.now()
        run.save()
        raise
