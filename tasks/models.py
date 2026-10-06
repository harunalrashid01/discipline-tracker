from django.db import models
from django.utils import timezone


class Category(models.Model):
    """
    A category for tasks (e.g. Health, Work, Study, Personal).
    Supports soft-delete via is_active flag.
    """

    name = models.CharField(max_length=100, unique=True, help_text="Category name (e.g. Health, Work, Study)")
    icon = models.CharField(max_length=20, blank=True, default="📁", help_text="Emoji icon for this category")
    color = models.CharField(
        max_length=30,
        blank=True,
        default="#6c757d",
        help_text="Badge color as CSS hex or name (e.g. #e74c3c)",
    )
    order = models.PositiveIntegerField(default=1, help_text="Display order — lower number appears first")
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive categories are hidden from task forms (soft delete)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name


class Task(models.Model):
    """
    A task that appears in the daily task list.

    task_type controls WHEN this task appears:
      'permanent' → every non-Sunday day
      'odd'       → Monday, Wednesday, Friday
      'even'      → Tuesday, Thursday, Saturday
      'today'     → Assigned date only
      'weekday'   → Specific day of week (Monday=0 ... Sunday=6)
      'date'      → Specific calendar dates (via TaskDateAssignment)
    """

    PERMANENT = "permanent"
    ODD = "odd"
    EVEN = "even"
    TODAY = "today"
    WEEKDAY = "weekday"
    DATE = "date"

    TASK_TYPE_CHOICES = [
        (PERMANENT, "Every Day (Permanent)"),
        (ODD, "Odd Days (Mon/Wed/Fri)"),
        (EVEN, "Even Days (Tue/Thu/Sat)"),
        (TODAY, "Today Only"),
        (WEEKDAY, "Specific Weekday"),
        (DATE, "Particular Date(s)"),
    ]

    WEEKDAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ANYTIME = "anytime"

    TIME_SLOT_CHOICES = [
        (MORNING, "🌅 Morning (5:30 AM – 10:00 AM)"),
        (AFTERNOON, "☀️ Afternoon (10:00 AM – 6:00 PM)"),
        (EVENING, "🌙 Evening (6:00 PM – 10:00 PM)"),
        (ANYTIME, "⚡ All Day / Any Time"),
    ]

    title = models.CharField(max_length=255, help_text="Short name of the task")
    description = models.TextField(blank=True, help_text="Optional longer description")
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        default=PERMANENT,
        help_text="Which days this task appears",
    )
    time_slot = models.CharField(
        max_length=20,
        choices=TIME_SLOT_CHOICES,
        default=ANYTIME,
        help_text="Section/time of day for this task",
    )
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        help_text="Day of the week for Specific Weekday tasks (0=Monday, 6=Sunday)",
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text="Display order — lower number appears first",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive tasks are hidden from the daily view",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
        help_text="Category this task belongs to (optional)",
    )

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self):
        return f"[{self.get_task_type_display()}] #{self.order} — {self.title}"

    def is_completed_on(self, target_date):
        """
        Check if this task has a completion record for a given date.
        """
        return TaskCompletion.objects.filter(task=self, date=target_date).exists()

    def is_available_on(self, target_date):
        """
        Determine whether this task is active and applicable to target_date.
        """
        if not self.is_active:
            return False

        w = target_date.weekday()

        if self.task_type == self.PERMANENT:
            return w != 6
        elif self.task_type == self.ODD:
            return w in (0, 2, 4)
        elif self.task_type == self.EVEN:
            return w in (1, 3, 5)
        elif self.task_type == self.TODAY:
            return self.date_assignments.filter(date=target_date).exists()
        elif self.task_type == self.WEEKDAY:
            return self.weekday == w
        elif self.task_type == self.DATE:
            return self.date_assignments.filter(date=target_date).exists()
        return False

    def get_assignment_display(self):
        """
        Returns a friendly string describing when this task appears.
        """
        if self.task_type == self.PERMANENT:
            return "Permanent"
        elif self.task_type == self.ODD:
            return "Odd (Mon/Wed/Fri)"
        elif self.task_type == self.EVEN:
            return "Even (Tue/Thu/Sat)"
        elif self.task_type == self.TODAY:
            assignment = self.date_assignments.first()
            if assignment:
                return f"Today — {assignment.date.strftime('%d/%m/%Y')}"
            return "Today Only"
        elif self.task_type == self.WEEKDAY:
            return f"{self.get_weekday_display()}" if self.weekday is not None else "Specific Weekday"
        elif self.task_type == self.DATE:
            dates = [d.date.strftime("%d/%m/%Y") for d in self.date_assignments.all()]
            return f"Dates — {', '.join(dates)}" if dates else "Particular Date(s)"
        return self.get_task_type_display()

    def get_time_slot_icon(self):
        icons = {
            self.MORNING: "🌅",
            self.AFTERNOON: "☀️",
            self.EVENING: "🌙",
            self.ANYTIME: "⚡",
        }
        return icons.get(self.time_slot, "⚡")

    def get_time_slot_short_label(self):
        labels = {
            self.MORNING: "Morning",
            self.AFTERNOON: "Afternoon",
            self.EVENING: "Evening",
            self.ANYTIME: "Anytime",
        }
        return labels.get(self.time_slot, "Anytime")


class TaskDateAssignment(models.Model):
    """
    Stores assigned dates for 'today' and 'date' task types.
    Enforces uniqueness per (task, date).
    """

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="date_assignments",
    )
    date = models.DateField(help_text="The date on which this task is assigned to appear")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "date"],
                name="unique_task_assignment_date",
            )
        ]
        ordering = ["date"]
        verbose_name = "Task Date Assignment"
        verbose_name_plural = "Task Date Assignments"

    def __str__(self):
        return f"{self.task.title} on {self.date}"


class TaskCompletion(models.Model):
    """
    Records that a specific Task was completed on a specific date.
    """

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    date = models.DateField(help_text="The date on which this task was completed")
    completed_at = models.DateTimeField(default=timezone.now, help_text="Exact timestamp")

    class Meta:
        unique_together = ("task", "date")
        ordering = ["-date", "task__order"]
        verbose_name = "Task Completion"
        verbose_name_plural = "Task Completions"

    def __str__(self):
        return f"{self.task.title} — completed on {self.date}"


class Countdown(models.Model):
    """
    Database-driven countdown target date.
    """

    title = models.CharField(max_length=255, default="DAYS REMAINING")
    target_date = models.DateField(help_text="Target date for countdown")
    subtitle = models.TextField(blank=True, help_text="Subtitle or description of the goal")
    is_active = models.BooleanField(default=True)
    is_final = models.BooleanField(default=False, help_text="Display as a small Final Countdown card at the bottom of the page")
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "target_date"]
        verbose_name = "Countdown"
        verbose_name_plural = "Countdowns"

    def __str__(self):
        return f"{self.title} ({self.target_date})"

    def get_countdown_info(self, today=None):
        if today is None:
            today = timezone.localdate()
        delta = (self.target_date - today).days
        if delta > 0:
            status = "countdown"
        elif delta == 0:
            status = "today"
        else:
            status = "passed"

        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "target_date": self.target_date,
            "days_remaining": max(delta, 0),
            "raw_days": delta,
            "status": status,
            "is_final": self.is_final,
        }


class MotivationQuote(models.Model):
    """
    Database-driven motivation quote.
    """

    quote = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Motivation Quote"
        verbose_name_plural = "Motivation Quotes"

    def __str__(self):
        return self.quote[:50] + ("..." if len(self.quote) > 50 else "")


class Goal(models.Model):
    """
    Database-driven goal card.
    """

    icon = models.CharField(max_length=20, blank=True, help_text="Emoji or icon character")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Goal"
        verbose_name_plural = "Goals"

    def __str__(self):
        return f"{self.icon} {self.title}" if self.icon else self.title


class DisciplineSettings(models.Model):
    """
    Singleton for configurable homepage and site text.
    """

    site_title = models.CharField(max_length=255, default="Discipline Tracker")
    progress_label = models.CharField(max_length=255, default="TODAY'S PROGRESS")
    streak_label = models.CharField(max_length=255, default="DAY STREAK")
    no_tasks_text = models.CharField(max_length=255, default="No tasks found for today.")
    add_task_btn_text = models.CharField(max_length=255, default="Add Your First Task")
    all_done_text = models.CharField(max_length=255, default="All tasks complete! You're incredible today.")
    today_is_day_text = models.CharField(max_length=255, default="TODAY IS THE DAY 🎯")
    day_arrived_text = models.CharField(max_length=255, default="THE DAY HAS ARRIVED")
    footer_text = models.CharField(max_length=255, default="Stay disciplined. Every day counts. 🔥")
    sunday_title = models.CharField(max_length=255, default="SUNDAY")
    sunday_subtitle = models.CharField(max_length=255, default="REST DAY")
    sunday_quote = models.TextField(default="Rest today. Come back stronger tomorrow.")
    sunday_note = models.TextField(default="Your tasks will be ready for you Monday morning.\nYour history is safe. Your streak is protected.")
    doc_url = models.URLField(
        max_length=500,
        blank=True,
        default="https://docs.google.com/document/d/1EUy5pCKRBcIBKGc56-pm74g43KovDhhBKnOp9XN2cvw/edit?tab=t.fbdjrcr8y6u7",
        help_text="Google Docs / Resource link for homepage button",
    )
    doc_button_text = models.CharField(
        max_length=100,
        default="📄 Open Important Notes / Guide",
        help_text="Button text for the doc link",
    )

    class Meta:
        verbose_name = "Discipline Settings"
        verbose_name_plural = "Discipline Settings"

    def __str__(self):
        return "Discipline Settings"

    @classmethod
    def get_settings(cls):
        settings_obj = cls.objects.first()
        if not settings_obj:
            settings_obj = cls.objects.create()
        return settings_obj

