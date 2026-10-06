"""
Root URL configuration for the Discipline Tracker.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Django admin panel at /admin/
    path("admin/", admin.site.urls),

    # Auth: login and logout
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # All task-related URLs are handled by the tasks app
    path("", include("tasks.urls")),
]
