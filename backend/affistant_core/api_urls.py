from django.urls import path
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok", "service": "affistant-api"})


urlpatterns = [
    path("health/", health_check),
]
