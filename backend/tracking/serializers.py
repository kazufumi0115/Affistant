from rest_framework import serializers
from .models import Keyword, ExtractionRun, SearchResult, MediaSite


class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = "__all__"


class ExtractionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionRun
        fields = "__all__"


class SearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchResult
        fields = "__all__"


class MediaSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaSite
        fields = "__all__"
