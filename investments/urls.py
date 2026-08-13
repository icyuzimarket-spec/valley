from django.urls import path

from . import views

app_name = "investments"

urlpatterns = [
    path("plans/", views.plan_list_view, name="plan_list"),
    path("invest/<int:plan_id>/", views.invest_view, name="invest"),
]
