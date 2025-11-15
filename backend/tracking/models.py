from django.db import models
from django.utils import timezone


class Keyword(models.Model):
    """
    トラッキングする検索キーワード
    """

    text = models.CharField(max_length=512, db_index=True)
    search_engine = models.CharField(max_length=32, default="google")  # 拡張用
    region = models.CharField(max_length=32, blank=True, null=True)  # ex: 'jp', 'us'
    locale = models.CharField(max_length=16, blank=True, null=True)  # ex: 'ja-JP'
    top_n = models.PositiveSmallIntegerField(default=20)  # 取得する上位N件
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.text


class ExtractionRun(models.Model):
    """
    1回の抽出実行（キーワード単位でもバッチでも可）
    """

    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="runs")
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=32,
        choices=[("pending", "pending"), ("running", "running"), ("success", "success"), ("failed", "failed")],
        default="pending",
    )
    note = models.TextField(blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)  # 必要なら保存（注意：サイズ）
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]


class MediaSite(models.Model):
    """
    ドメインベースの情報。複数のSearchResultが同ドメインを参照する。
    """

    domain = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=512, blank=True, null=True)
    site_type = models.CharField(max_length=64, blank=True, null=True)  # ex: blog, ecommerce, news
    last_seen = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.domain


class SearchResult(models.Model):
    """
    検索結果の1エントリ（順位ごと）
    """

    run = models.ForeignKey(ExtractionRun, on_delete=models.CASCADE, related_name="results")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="results")
    position = models.IntegerField()  # 1..N
    is_ad = models.BooleanField(default=False)
    url = models.URLField()
    domain = models.CharField(max_length=255, db_index=True)
    title = models.CharField(max_length=1024, blank=True, null=True)
    snippet = models.TextField(blank=True, null=True)
    estimated_traffic = models.BigIntegerField(blank=True, null=True)  # 任意の推定流入数
    metrics = models.JSONField(blank=True, null=True)  # 追加メトリクス（例: page_speed 等）
    fetched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["keyword", "position"]
        indexes = [
            models.Index(fields=["keyword", "position"]),
            models.Index(fields=["domain"]),
        ]

    def __str__(self):
        return f"{self.keyword.text} #{self.position} - {self.domain}"
