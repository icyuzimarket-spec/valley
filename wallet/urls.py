from django.urls import path

from . import views

app_name = "wallet"

urlpatterns = [
    path("withdraw/", views.withdraw_view, name="withdraw"),
    path("countdown/", views.countdown_clock_view, name="countdown"),
]
