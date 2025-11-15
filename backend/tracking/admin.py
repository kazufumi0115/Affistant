from django.contrib import admin
from .models import Keyword, ExtractionRun, SearchResult, MediaSite


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("text", "search_engine", "top_n", "is_active", "created_at")
    search_fields = ("text",)


@admin.register(ExtractionRun)
class RunAdmin(admin.ModelAdmin):
    list_display = ("keyword", "status", "started_at", "finished_at")


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    list_display = ("keyword", "position", "domain", "title", "fetched_at")
    search_fields = ("url", "domain", "title")


@admin.register(MediaSite)
class MediaSiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "site_type", "last_seen")
