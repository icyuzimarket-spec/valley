from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("dashboard/", views.dashboard_redirect_view, name="dashboard_redirect"),
    path("dashboard/me/", views.user_dashboard_view, name="user_dashboard"),
    path("dashboard/admin/", views.admin_dashboard_view, name="admin_dashboard"),
    path("management/users/", views.user_management_users_view, name="management_users"),
    path("management/investments/", views.user_management_investments_view, name="management_investments"),
    path("management/withdrawals/", views.user_management_withdrawals_view, name="management_withdrawals"),
]
