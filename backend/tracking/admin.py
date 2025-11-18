from django.contrib import admin
from .models import Genre, Project, Keyword, MediaSite, ExtractionRun, SearchResult, AffiliateLink

# モデルの管理画面での表示をカスタマイズします


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """
    ジャンル モデルの管理画面設定
    """

    list_display = ("name", "owner", "created_at")
    search_fields = ("name",)
    list_filter = ("owner",)
    ordering = ("-created_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    案件（プロジェクト）モデルの管理画面設定
    """

    list_display = ("name", "genre", "owner", "created_at")
    search_fields = ("name",)
    list_filter = ("genre", "owner")
    ordering = ("-created_at",)


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    """
    キーワード モデルの管理画面設定
    """

    list_display = ("text", "project", "search_volume", "created_at")
    search_fields = ("text",)
    list_filter = ("project__name",)
    ordering = ("-created_at",)


@admin.register(MediaSite)
class MediaSiteAdmin(admin.ModelAdmin):
    """
    メディアサイト モデルの管理画面設定
    """

    list_display = ("domain", "name")
    search_fields = ("domain", "name")


@admin.register(ExtractionRun)
class ExtractionRunAdmin(admin.ModelAdmin):
    """
    検索実行履歴 モデルの管理画面設定
    """

    list_display = ("project", "executed_at", "max_rank", "status")
    list_filter = ("project__name", "status")
    date_hierarchy = "executed_at"
    ordering = ("-executed_at",)


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    """
    検索結果 モデルの管理画面設定
    """

    list_display = ("keyword", "rank", "media_site", "title", "run")
    search_fields = ("keyword__text", "media_site__domain", "page_url", "title")
    list_filter = ("run", "media_site")
    ordering = ("run", "keyword", "rank")


@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    """
    アフィリエイトリンク モデルの管理画面設定
    """

    list_display = ("link_url", "asp_name", "product_name", "search_result")
    search_fields = ("link_url", "asp_name", "product_name")
    list_filter = ("asp_name",)
