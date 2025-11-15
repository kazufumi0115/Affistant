from rest_framework.routers import DefaultRouter
from .views import KeywordViewSet, ExtractionRunViewSet, SearchResultViewSet, MediaSiteViewSet

router = DefaultRouter()
router.register(r"keywords", KeywordViewSet, basename="keyword")
router.register(r"runs", ExtractionRunViewSet, basename="run")
router.register(r"results", SearchResultViewSet, basename="result")
router.register(r"media", MediaSiteViewSet, basename="media")

urlpatterns = router.urls
