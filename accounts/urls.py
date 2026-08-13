from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.PhoneLoginView.as_view(), name="login"),
    path("logout/", views.PhoneLogoutView.as_view(), name="logout"),
    path("profile/", views.profile_view, name="profile"),
]
