from rest_framework import serializers
from .models import Genre, Project, Keyword, MediaSite, ExtractionRun, SearchResult, AffiliateLink


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "owner", "created_at"]
        read_only_fields = ["owner"]  # オーナーは自動的に設定


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "genre", "owner", "created_at"]
        read_only_fields = ["owner"]


class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ["id", "project", "text", "search_volume", "created_at"]


class MediaSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaSite
        fields = ["id", "domain", "name"]


class ExtractionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionRun
        fields = ["id", "project", "max_rank", "executed_at"]


class AffiliateLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliateLink
        fields = ["id", "link_url", "asp_name", "product_name"]


class SearchResultSerializer(serializers.ModelSerializer):
    affiliate_links = AffiliateLinkSerializer(many=True, read_only=True)

    class Meta:
        model = SearchResult
        fields = ["id", "run", "keyword", "media_site", "rank", "page_url", "title", "affiliate_links"]
