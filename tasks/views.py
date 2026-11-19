from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CategoryForm, TaskForm
from .models import (
    Category,
    Countdown,
    DisciplineSettings,
    Goal,
    MotivationQuote,
    Task,
    TaskCompletion,
)


# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_day_type(today: date) -> str:
    """
    Returns the type of day based on weekday:
      Monday=0, Tuesday=1, Wednesday=2, Thursday=3,
      Friday=4, Saturday=5, Sunday=6
    """
    weekday = today.weekday()
    if weekday == 6:
        return "holiday"
    elif weekday in (0, 2, 4):   # Mon, Wed, Fri
        return "odd"
    else:                         # Tue, Thu, Sat
        return "even"


def get_current_time_slot(now_dt=None) -> str:
    """
    Returns the active time slot based on local time:
      'morning'   : 05:30 to 10:00 (5:30 AM – 10:00 AM)
      'afternoon' : 10:00 to 18:00 (10:00 AM – 6:00 PM)
      'evening'   : 18:00 to 05:30 (6:00 PM – 5:30 AM)
    """
    if now_dt is None:
        now_dt = timezone.localtime()
    total_minutes = now_dt.hour * 60 + now_dt.minute
    if 330 <= total_minutes < 600:
        return "morning"
    elif 600 <= total_minutes < 1080:
        return "afternoon"
    else:
        return "evening"


def is_task_available_on(task: Task, today: date) -> bool:
    """
    Determine whether a task is actually assigned to and available on a given date.
    """
    return task.is_available_on(today)


def get_applicable_tasks_query(target_date: date):
    """
    Builds the Q filter for tasks applicable on target_date.
    """
    weekday = target_date.weekday()
    conditions = Q()

    if weekday != 6:
        conditions |= Q(task_type=Task.PERMANENT)

    if weekday in (0, 2, 4):
        conditions |= Q(task_type=Task.ODD)

    if weekday in (1, 3, 5):
        conditions |= Q(task_type=Task.EVEN)

    conditions |= Q(task_type=Task.TODAY, date_assignments__date=target_date)
    conditions |= Q(task_type=Task.WEEKDAY, weekday=weekday)
    conditions |= Q(task_type=Task.DATE, date_assignments__date=target_date)

    return conditions


def get_tasks_for_day(day_type: str, today: date):
    """
    Returns two lists: (pending_tasks, completed_tasks)
    Each item is a Task object annotated with .completed (bool).
    """
    conditions = get_applicable_tasks_query(today)

    tasks = (
        Task.objects.filter(is_active=True)
        .filter(conditions)
        .distinct()
        .order_by("order", "created_at")
    )

    completed_ids = set(
        TaskCompletion.objects.filter(
            task__in=tasks, date=today
        ).values_list("task_id", flat=True)
    )

    pending = []
    completed = []

    for task in tasks:
        task.completed = task.id in completed_ids
        if task.completed:
            completed.append(task)
        else:
            pending.append(task)

    return pending, completed


def get_countdown():
    """
    Legacy helper: returns the first active countdown or default.
    """
    today = timezone.localdate()
    first = Countdown.objects.filter(is_active=True).order_by("order", "target_date").first()
    if first:
        return first.get_countdown_info(today)
    return {
        "title": "DAYS REMAINING",
        "subtitle": "",
        "days_remaining": 0,
        "raw_days": 0,
        "status": "today",
        "target_date": today,
    }


def get_streak():
    """
    Calculate consecutive days where at least one task was completed.
    Checks backwards from yesterday.
    """
    today = timezone.localdate()
    streak = 0
    check_date = today - timedelta(days=1)

    for _ in range(365):
        count = TaskCompletion.objects.filter(date=check_date).count()
        if count > 0:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak


# ─── Views ───────────────────────────────────────────────────────────────────

@login_required
def home(request):
    """
    Main homepage — shows database-driven countdowns, motivation, and today's tasks.
    Active category is persisted in the database (synced across all devices).
    """
    today = timezone.localdate()
    day_type = get_day_type(today)

    all_categories = Category.objects.filter(is_active=True).order_by("order", "name")
    site_settings = DisciplineSettings.get_settings()

    # ── Category filter: save to DB so all devices stay in sync ───
    if "category_id" in request.GET:
        raw = request.GET.get("category_id", "")
        if raw == "all":
            site_settings.active_category = None
        else:
            try:
                cat_id = int(raw)
                cat = all_categories.filter(id=cat_id).first()
                site_settings.active_category = cat  # None if not found
            except (ValueError, TypeError):
                site_settings.active_category = None
        site_settings.save(update_fields=["active_category"])
        return redirect("home")

    # Read active category from DB
    selected_category = site_settings.active_category
    # Guard: if the category was deleted/deactivated, clear it
    if selected_category and not all_categories.filter(id=selected_category.id).exists():
        site_settings.active_category = None
        site_settings.save(update_fields=["active_category"])
        selected_category = None

    active_countdowns = Countdown.objects.filter(is_active=True).order_by("order", "target_date")
    all_countdowns = [c.get_countdown_info(today) for c in active_countdowns]
    countdowns = [c for c in all_countdowns if not c.get("is_final")]
    final_countdowns = [c for c in all_countdowns if c.get("is_final")]
    countdown = countdowns[0] if countdowns else None

    quotes = MotivationQuote.objects.filter(is_active=True).order_by("order", "id")
    goals = Goal.objects.filter(is_active=True).order_by("order", "id")
    streak = get_streak()

    pending, completed = get_tasks_for_day(day_type, today)

    # Apply category filter if one is selected
    if selected_category:
        pending = [t for t in pending if t.category_id == selected_category.id]
        completed = [t for t in completed if t.category_id == selected_category.id]

    total = len(pending) + len(completed)
    done_count = len(completed)
    progress_pct = int((done_count / total * 100)) if total > 0 else 0

    day_names = {
        "odd": "ODD DAY",
        "even": "EVEN DAY",
        "holiday": "SUNDAY",
    }

    context = {
        "today": today,
        "day_type": day_type,
        "day_label": day_names.get(day_type, ""),
        "pending_tasks": pending,
        "completed_tasks": completed,
        "total": total,
        "done_count": done_count,
        "progress_pct": progress_pct,
        "countdowns": countdowns,
        "countdown": countdown,
        "final_countdowns": final_countdowns,
        "final_countdown": final_countdowns[0] if final_countdowns else None,
        "quotes": quotes,
        "goals": goals,
        "site_settings": site_settings,
        "streak": streak,
        "all_categories": all_categories,
        "selected_category": selected_category,
    }

    return render(request, "home.html", context)


@login_required
@require_POST
def complete_task(request, task_id):
    """
    AJAX endpoint: mark a task as completed for today.
    Validates task availability for today before completing.
    """
    task = get_object_or_404(Task, id=task_id, is_active=True)
    today = timezone.localdate()

    if not is_task_available_on(task, today):
        return JsonResponse({
            "status": "error",
            "message": "This task is not available today."
        }, status=400)

    completion, created = TaskCompletion.objects.get_or_create(
        task=task,
        date=today,
        defaults={"completed_at": timezone.now()},
    )

    day_type = get_day_type(today)
    pending, completed = get_tasks_for_day(day_type, today)
    total = len(pending) + len(completed)
    done_count = len(completed)
    progress_pct = int((done_count / total * 100)) if total > 0 else 0

    return JsonResponse({
        "status": "ok",
        "created": created,
        "done_count": done_count,
        "total": total,
        "progress_pct": progress_pct,
    })


@login_required
@require_POST
def undo_task(request, task_id):
    """
    AJAX endpoint: undo a task completion for today.
    Validates task availability for today before undoing.
    """
    task = get_object_or_404(Task, id=task_id)
    today = timezone.localdate()

    if not is_task_available_on(task, today):
        return JsonResponse({
            "status": "error",
            "message": "This task is not available today."
        }, status=400)

    TaskCompletion.objects.filter(task=task, date=today).delete()

    day_type = get_day_type(today)
    pending, completed = get_tasks_for_day(day_type, today)
    total = len(pending) + len(completed)
    done_count = len(completed)
    progress_pct = int((done_count / total * 100)) if total > 0 else 0

    return JsonResponse({
        "status": "ok",
        "done_count": done_count,
        "total": total,
        "progress_pct": progress_pct,
    })


@login_required
def history(request):
    """
    History page — shows completion summary grouped by date.
    Calculates applicable task totals for all assignment types across history.
    """
    history_data = (
        TaskCompletion.objects
        .values("date")
        .annotate(completed_count=Count("id"))
        .order_by("-date")[:60]
    )

    site_settings = DisciplineSettings.get_settings()
    enriched = []
    for entry in history_data:
        d = entry["date"]
        conditions = get_applicable_tasks_query(d)
        total_for_day = Task.objects.filter(is_active=True).filter(conditions).distinct().count()

        enriched.append({
            "date": d,
            "completed": entry["completed_count"],
            "total": total_for_day,
            "pct": int(entry["completed_count"] / total_for_day * 100) if total_for_day else 0,
        })

    context = {
        "history": enriched,
        "site_settings": site_settings,
    }
    return render(request, "history.html", context)


@login_required
def manage_tasks(request):
    """
    Task management page — list all tasks with edit/delete options.
    """
    tasks = Task.objects.all().order_by("task_type", "order")
    site_settings = DisciplineSettings.get_settings()
    context = {
        "tasks": tasks,
        "site_settings": site_settings,
    }
    return render(request, "manage_tasks.html", context)


@login_required
def add_task(request):
    """
    Add a new task via a form.
    Pre-fills category from session if one is selected.
    """
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            # Persist selected category to session
            if task.category_id:
                request.session["selected_category_id"] = task.category_id
            return redirect("manage_tasks")
    else:
        form = TaskForm()
        # Pre-fill category from session
        selected_category_id = request.session.get("selected_category_id")
        if selected_category_id:
            form.initial["category"] = selected_category_id

    return render(request, "task_form.html", {"form": form, "action": "Add"})


@login_required
def edit_task(request, task_id):
    """
    Edit an existing task.
    """
    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("manage_tasks")
    else:
        form = TaskForm(instance=task)

    return render(request, "task_form.html", {"form": form, "action": "Edit", "task": task})


@login_required
def delete_task(request, task_id):
    """
    Delete a task (with confirmation).
    """
    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        task.delete()
        return redirect("manage_tasks")

    return render(request, "delete_task.html", {"task": task})


# ─── Category CRUD ───────────────────────────────────────────────────────────

@login_required
def manage_categories(request):
    """
    List all categories with edit / delete options.
    """
    categories = Category.objects.all().order_by("order", "name")
    site_settings = DisciplineSettings.get_settings()
    return render(request, "manage_categories.html", {
        "categories": categories,
        "site_settings": site_settings,
    })


@login_required
def add_category(request):
    """
    Create a new category.
    """
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created successfully.")
            return redirect("manage_categories")
    else:
        form = CategoryForm()
    site_settings = DisciplineSettings.get_settings()
    return render(request, "category_form.html", {
        "form": form,
        "action": "Add",
        "site_settings": site_settings,
    })


@login_required
def edit_category(request, category_id):
    """
    Edit an existing category.
    """
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("manage_categories")
    else:
        form = CategoryForm(instance=category)
    site_settings = DisciplineSettings.get_settings()
    return render(request, "category_form.html", {
        "form": form,
        "action": "Edit",
        "category": category,
        "site_settings": site_settings,
    })


@login_required
def delete_category(request, category_id):
    """
    Soft-delete (deactivate) a category, or hard-delete if confirmed.
    """
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        action = request.POST.get("action", "soft")
        if action == "hard":
            category.delete()
            messages.success(request, f"Category '{category.name}' permanently deleted.")
        else:
            category.is_active = False
            category.save()
            messages.success(request, f"Category '{category.name}' deactivated (soft deleted).")
        return redirect("manage_categories")
    site_settings = DisciplineSettings.get_settings()
    return render(request, "delete_category.html", {
        "category": category,
        "site_settings": site_settings,
    })

