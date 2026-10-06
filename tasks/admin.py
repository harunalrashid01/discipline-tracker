from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    Countdown,
    DisciplineSettings,
    Goal,
    MotivationQuote,
    Task,
    TaskCompletion,
    TaskDateAssignment,
)


# ─── Category ────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["order", "color_badge", "name", "icon", "task_count", "is_active"]
    list_display_links = ["name"]
    list_editable = ["order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["order", "name"]

    fieldsets = (
        (None, {
            "fields": ("name", "icon", "color", "order", "is_active"),
            "description": (
                "Categories are used to group tasks. "
                "Set <b>is_active = False</b> to soft-delete a category "
                "(it will be hidden from the task form but not removed from the database)."
            ),
        }),
    )

    # ── Custom display columns ──────────────────────────────────────────────

    @admin.display(description="Color")
    def color_badge(self, obj):
        return format_html(
            '<span style="display:inline-block;width:18px;height:18px;border-radius:4px;'
            'background:{};border:1px solid #555;vertical-align:middle;"></span>',
            obj.color or "#6c757d",
        )

    @admin.display(description="Tasks")
    def task_count(self, obj):
        return obj.tasks.count()

    # ── Soft-delete actions ─────────────────────────────────────────────────

    actions = ["soft_delete_categories", "restore_categories"]

    @admin.action(description="🗑 Soft-delete selected categories (hide from task form)")
    def soft_delete_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} category/categories deactivated (soft-deleted).")

    @admin.action(description="✅ Restore selected categories (make active again)")
    def restore_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} category/categories restored.")

    def has_delete_permission(self, request, obj=None):
        """
        Disable the hard-delete button so soft-delete is always used.
        Allow only superusers to hard-delete.
        """
        return request.user.is_superuser


# ─── Task ─────────────────────────────────────────────────────────────────────

class TaskDateAssignmentInline(admin.TabularInline):
    model = TaskDateAssignment
    extra = 1


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["order", "title", "category_badge", "task_type", "time_slot", "weekday_display", "is_active", "updated_at"]
    list_display_links = ["title"]
    list_filter = ["task_type", "time_slot", "category", "is_active", "weekday"]
    search_fields = ["title", "description"]
    list_editable = ["order", "is_active"]
    ordering = ["order", "created_at"]
    inlines = [TaskDateAssignmentInline]

    fieldsets = (
        (None, {
            "fields": ("title", "description")
        }),
        ("Scheduling & Section", {
            "fields": ("task_type", "time_slot", "weekday", "order", "is_active"),
            "description": "Control when, in which time section, and whether this task appears.",
        }),
        ("Category", {
            "fields": ("category",),
            "description": "Optional: assign a category to group this task.",
        }),
    )

    @admin.display(description="Weekday")
    def weekday_display(self, obj):
        if obj.task_type == Task.WEEKDAY and obj.weekday is not None:
            return obj.get_weekday_display()
        return "-"

    @admin.display(description="Category")
    def category_badge(self, obj):
        if obj.category:
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px;">'
                "{} {}"
                "</span>",
                obj.category.color or "#6c757d",
                obj.category.icon or "",
                obj.category.name,
            )
        return "-"


# ─── TaskDateAssignment ───────────────────────────────────────────────────────

@admin.register(TaskDateAssignment)
class TaskDateAssignmentAdmin(admin.ModelAdmin):
    list_display = ["task", "date"]
    list_filter = ["date", "task__task_type"]
    search_fields = ["task__title"]
    date_hierarchy = "date"
    ordering = ["-date"]


# ─── TaskCompletion ───────────────────────────────────────────────────────────

@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ["task", "date", "completed_at"]
    list_filter = ["date"]
    search_fields = ["task__title"]
    date_hierarchy = "date"
    ordering = ["-date", "task__order"]


# ─── Countdown ────────────────────────────────────────────────────────────────

@admin.register(Countdown)
class CountdownAdmin(admin.ModelAdmin):
    list_display = ["order", "title", "target_date", "is_final", "subtitle", "is_active"]
    list_display_links = ["title"]
    list_editable = ["order", "is_active", "is_final"]
    list_filter = ["is_active", "is_final", "target_date"]
    search_fields = ["title", "subtitle"]
    ordering = ["order", "target_date"]


# ─── MotivationQuote ──────────────────────────────────────────────────────────

@admin.register(MotivationQuote)
class MotivationQuoteAdmin(admin.ModelAdmin):
    list_display = ["order", "quote_preview", "is_active"]
    list_display_links = ["quote_preview"]
    list_editable = ["order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["quote"]
    ordering = ["order", "id"]

    @admin.display(description="Quote")
    def quote_preview(self, obj):
        return obj.quote[:60] + ("..." if len(obj.quote) > 60 else "")


# ─── Goal ─────────────────────────────────────────────────────────────────────

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["order", "icon", "title", "description", "is_active"]
    list_display_links = ["title"]
    list_editable = ["order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["title", "description"]
    ordering = ["order", "id"]


# ─── DisciplineSettings ───────────────────────────────────────────────────────

@admin.register(DisciplineSettings)
class DisciplineSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "site_title", "progress_label"]

    def has_add_permission(self, request):
        if DisciplineSettings.objects.exists():
            return False
        return super().has_add_permission(request)

