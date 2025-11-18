from celery import shared_task
from .models import ExtractionRun, Keyword, SearchResult, MediaSite

# (注: スクレイピングロジック（bs4, requests）もここでインポートします)
import requests
from bs4 import BeautifulSoup


@shared_task(bind=True)
def enqueue_extraction_for_keyword(self, run_id, keyword_id):
    """
    Celeryワーカーが実行するタスク。
    単一のExtractionRunと単一のKeyword IDを受け取り、
    スクレイピングを実行して SearchResult を保存する。
    """
    try:
        run = ExtractionRun.objects.get(id=run_id)
        keyword = Keyword.objects.get(id=keyword_id)

        # 実行ステータスを 'running' に更新
        # (注: 複数のワーカーが同時に status を更新しようとする競合が
        # 発生しうるため、run全体のステータス更新はタスク呼び出し側で行う方が安全かもしれません)
        # ここではタスク開始のログとして残します
        print(f"Task started for: run_id={run_id}, keyword='{keyword.text}'")

        # === スクレイピングロジック (ダミー) ===
        # (要件定義: ①-5, A〜Gの情報を取得)
        # ここに requests と bs4 を使ったGoogle検索結果の
        # スクレイピングロジックを実装します。

        # (ダミーの検索結果)
        dummy_rank = 1
        dummy_url = f"https://example-media.com/{keyword.text.replace(' ', '-')}"
        dummy_title = f"【1位】{keyword.text} のおすすめ！"

        # MediaSiteモデルはドメインで管理
        media_site, _ = MediaSite.objects.get_or_create(domain="example-media.com", defaults={"name": "Example Media"})

        # SearchResultを保存
        search_result = SearchResult.objects.create(
            run=run, keyword=keyword, media_site=media_site, rank=dummy_rank, page_url=dummy_url, title=dummy_title
        )
        # (この後、AffiliateLinkモデルも保存)

        # === スクレイピングロジック完了 ===

        # (注: run全体のステータス更新は、全タスクの完了を
        # 監視する別のメカニズムが必要です。
        # ここでは個別のタスク成功として扱います。)

        print(f"Task completed for: {keyword.text}")
        return f"Success: {keyword.text}"

    except Keyword.DoesNotExist:
        return f"Error: Keyword {keyword_id} not found."
    except ExtractionRun.DoesNotExist:
        return f"Error: ExtractionRun {run_id} not found."
    except Exception as e:
        # エラーが発生した場合、タスクをリトライ
        self.retry(exc=e, countdown=60)
        return f"Error: {str(e)}"


# (注: Celeryがこのファイルを見つけられるように、
# affiysan_core/celery.py や settings.py の設定が
# 正しく行われているか確認してください)
