from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Keyword, ExtractionRun, SearchResult, MediaSite
from .serializers import KeywordSerializer, ExtractionRunSerializer, SearchResultSerializer, MediaSiteSerializer
from .tasks import enqueue_extraction_for_keyword


class KeywordViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer

    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        keyword = self.get_object()
        run = ExtractionRun.objects.create(keyword=keyword, status="pending")
        enqueue_extraction_for_keyword.delay(run.id)  # Celeryタスク
        return Response({"run_id": run.id, "status": run.status}, status=status.HTTP_202_ACCEPTED)


class ExtractionRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExtractionRun.objects.all()
    serializer_class = ExtractionRunSerializer


class SearchResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SearchResult.objects.all()
    serializer_class = SearchResultSerializer


class MediaSiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MediaSite.objects.all()
    serializer_class = MediaSiteSerializer
