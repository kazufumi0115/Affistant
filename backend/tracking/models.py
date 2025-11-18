from django.db import models
from django.conf import settings  # ユーザーモデルを参照するために必要
from django.utils.translation import gettext_lazy as _


class Genre(models.Model):
    """
    プロジェクトを分類する「ジャンル」。
    （要件定義: ジャンル > 案件 の1階層目）
    """

    name = models.CharField(_("ジャンル名"), max_length=100, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("オーナー"), on_delete=models.CASCADE, related_name="genres"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    """
    分析対象の「案件」。
    （要件定義: ジャンル > 案件 の2階層目）
    """

    name = models.CharField(_("案件名"), max_length=255)
    genre = models.ForeignKey(
        Genre,
        verbose_name=_("ジャンル"),
        on_delete=models.SET_NULL,  # ジャンルが消えても案件は残す
        null=True,
        blank=True,
        related_name="projects",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("オーナー"), on_delete=models.CASCADE, related_name="projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Keyword(models.Model):
    """
    分析対象のSEOキーワード。プロジェクトに紐づく。
    """

    project = models.ForeignKey(Project, verbose_name=_("案件"), on_delete=models.CASCADE, related_name="keywords")
    text = models.CharField(_("キーワード"), max_length=255)
    search_volume = models.IntegerField(_("月間検索ボリューム"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "text")  # 同一プロジェクト内でキーワードはユニーク

    def __str__(self):
        return self.text


class MediaSite(models.Model):
    """
    検索結果で検出されたメディア（サイト）情報。
    """

    domain = models.CharField(_("ドメイン"), max_length=255, unique=True)
    name = models.CharField(_("メディア名"), max_length=255, blank=True)

    def __str__(self):
        return self.name or self.domain


class ExtractionRun(models.Model):
    """
    検索実行（スクレイピング）の履歴。
    """

    # === ▼ 修正 ▼ ===
    # statusフィールドの選択肢を定義
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("running", _("Running")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
    ]
    # === ▲ 修正 ▲ ===

    project = models.ForeignKey(Project, verbose_name=_("案件"), on_delete=models.CASCADE, related_name="runs")
    max_rank = models.IntegerField(_("最大抽出順位"), default=50)
    executed_at = models.DateTimeField(_("実行日時"), auto_now_add=True)

    # === ▼ 修正 ▼ ===
    # statusフィールドを追加
    # これにより admin.py と views.py が正しく動作するようになります
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    # === ▲ 修正 ▲ ===

    def __str__(self):
        return f"{self.project.name} @ {self.executed_at.strftime('%Y-%m-%d %H:%M')}"


class SearchResult(models.Model):
    """
    特定の検索実行における、キーワードごとの検索結果（記事）。
    """

    run = models.ForeignKey(ExtractionRun, verbose_name=_("実行履歴"), on_delete=models.CASCADE, related_name="results")
    keyword = models.ForeignKey(Keyword, verbose_name=_("キーワード"), on_delete=models.CASCADE, related_name="results")
    media_site = models.ForeignKey(
        MediaSite, verbose_name=_("メディアサイト"), on_delete=models.CASCADE, related_name="results"
    )
    rank = models.IntegerField(_("SEO順位"))
    page_url = models.URLField(_("掲載記事リンク"), max_length=2048)
    title = models.CharField(_("記事タイトル"), max_length=512, blank=True)

    def __str__(self):
        return f"[{self.rank}位] {self.keyword.text} - {self.media_site.domain}"


class AffiliateLink(models.Model):
    """
    (G) 記事内で検出されたアフィリエイトリンクの情報。
    """

    search_result = models.ForeignKey(
        SearchResult, verbose_name=_("検索結果記事"), on_delete=models.CASCADE, related_name="affiliate_links"
    )
    link_url = models.URLField(_("アフィリエイトリンクURL"), max_length=2048)
    asp_name = models.CharField(_("ASP名"), max_length=100, blank=True)
    product_name = models.CharField(_("商品名"), max_length=255, blank=True)

    def __str__(self):
        return self.link_url
