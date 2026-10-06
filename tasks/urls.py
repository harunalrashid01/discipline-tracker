"""
URL patterns for the tasks application.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Homepage (today's tasks)
    path("", views.home, name="home"),

    # AJAX endpoints (called by JavaScript — no page reload)
    path("tasks/complete/<int:task_id>/", views.complete_task, name="complete_task"),
    path("tasks/undo/<int:task_id>/", views.undo_task, name="undo_task"),

    # History page
    path("history/", views.history, name="history"),

    # Task management (CRUD)
    path("manage/", views.manage_tasks, name="manage_tasks"),
    path("manage/add/", views.add_task, name="add_task"),
    path("manage/edit/<int:task_id>/", views.edit_task, name="edit_task"),
    path("manage/delete/<int:task_id>/", views.delete_task, name="delete_task"),
]
