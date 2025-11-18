from django.urls import path
from users.views import LoginView, RegisterView, LogoutView

urlpatterns = [
    # /api/v1/auth/register/
    path("register/", RegisterView.as_view(), name="api_register"),
    # /api/v1/auth/login/
    path("login/", LoginView.as_view(), name="api_login"),
    # /api/v1/auth/logout/
    path("logout/", LogoutView.as_view(), name="api_logout"),
]
