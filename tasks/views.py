from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import (
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
    """
    today = timezone.localdate()
    day_type = get_day_type(today)

    active_countdowns = Countdown.objects.filter(is_active=True).order_by("order", "target_date")
    all_countdowns = [c.get_countdown_info(today) for c in active_countdowns]
    countdowns = [c for c in all_countdowns if not c.get("is_final")]
    final_countdowns = [c for c in all_countdowns if c.get("is_final")]
    countdown = countdowns[0] if countdowns else None

    quotes = MotivationQuote.objects.filter(is_active=True).order_by("order", "id")
    goals = Goal.objects.filter(is_active=True).order_by("order", "id")
    site_settings = DisciplineSettings.get_settings()
    streak = get_streak()

    pending, completed = get_tasks_for_day(day_type, today)
    total = len(pending) + len(completed)
    done_count = len(completed)
    progress_pct = int((done_count / total * 100)) if total > 0 else 0

    day_names = {
        "odd": "ODD DAY",
        "even": "EVEN DAY",
        "holiday": "SUNDAY",
    }

    current_time_slot = get_current_time_slot()
    slot_display_names = {
        "morning": "Morning (5:30 AM – 10:00 AM)",
        "afternoon": "Afternoon (10:00 AM – 6:00 PM)",
        "evening": "Evening (6:00 PM – 10:00 PM)",
    }
    slot_icons = {
        "morning": "🌅",
        "afternoon": "☀️",
        "evening": "🌙",
    }

    context = {
        "today": today,
        "day_type": day_type,
        "day_label": day_names.get(day_type, ""),
        "current_time_slot": current_time_slot,
        "current_slot_icon": slot_icons.get(current_time_slot, "🕒"),
        "current_time_slot_label": slot_display_names.get(current_time_slot, "Current Time"),
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
    """
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("manage_tasks")
    else:
        form = TaskForm()

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

