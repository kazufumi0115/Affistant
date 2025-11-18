from rest_framework.routers import DefaultRouter
from .views import (
    GenreViewSet,
    ProjectViewSet,
    KeywordViewSet,
    ExtractionRunViewSet,
    SearchResultViewSet,
    MediaSiteViewSet,
)

router = DefaultRouter()
router.register(r"genres", GenreViewSet, basename="genre")
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"keywords", KeywordViewSet, basename="keyword")
router.register(r"runs", ExtractionRunViewSet, basename="run")
router.register(r"results", SearchResultViewSet, basename="result")
router.register(r"media", MediaSiteViewSet, basename="media")

# app_name は DefaultRouter を使う場合は不要
# app_name = 'tracking'

urlpatterns = router.urls
