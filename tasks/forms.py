from datetime import datetime
from django import forms
from django.utils import timezone
from .models import Category, Task, TaskDateAssignment



class TaskForm(forms.ModelForm):
    dates = forms.CharField(
        required=False,
        label="Particular Date(s)",
        help_text="Enter dates in DD/MM/YYYY format, separated by commas (e.g. 05/09/2026, 12/09/2026)",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "e.g. 05/09/2026, 12/09/2026",
            "id": "id_dates",
        }),
    )

    class Meta:
        model = Task
        fields = ["title", "description", "task_type", "time_slot", "weekday", "category", "order", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. Learn English for 30 minutes",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "Optional details about this task...",
            }),
            "task_type": forms.Select(attrs={"class": "form-input", "id": "id_task_type"}),
            "time_slot": forms.Select(attrs={"class": "form-input", "id": "id_time_slot"}),
            "weekday": forms.Select(attrs={"class": "form-input", "id": "id_weekday"}),
            "category": forms.Select(attrs={"class": "form-input", "id": "id_category"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        labels = {
            "title": "Task Title",
            "description": "Description (optional)",
            "task_type": "Appears On",
            "time_slot": "Time Slot / Section",
            "weekday": "Specific Weekday",
            "category": "Category",
            "order": "Display Order",
            "is_active": "Active (visible in daily view)",
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "time_slot" in self.fields:
            self.fields["time_slot"].required = False
            self.fields["time_slot"].initial = Task.ANYTIME
        # Only show active categories; make it optional
        if "category" in self.fields:
            self.fields["category"].queryset = Category.objects.filter(is_active=True)
            self.fields["category"].required = False
            self.fields["category"].empty_label = "— No Category —"
        if self.instance and self.instance.pk:
            if self.instance.task_type == Task.DATE:
                assigned_dates = self.instance.date_assignments.values_list("date", flat=True).order_by("date")
                formatted = [d.strftime("%d/%m/%Y") for d in assigned_dates]
                self.fields["dates"].initial = ", ".join(formatted)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("time_slot"):
            cleaned_data["time_slot"] = Task.ANYTIME
        task_type = cleaned_data.get("task_type")
        weekday = cleaned_data.get("weekday")
        dates_raw = cleaned_data.get("dates")

        if task_type == Task.WEEKDAY:
            if weekday is None or weekday == "":
                self.add_error("weekday", "Please select a weekday for Specific Weekday tasks.")
        elif task_type == Task.DATE:
            if not dates_raw or not dates_raw.strip():
                self.add_error("dates", "Please provide at least one date in DD/MM/YYYY format.")
            else:
                parsed_dates = set()
                raw_parts = [p.strip() for p in dates_raw.replace(";", ",").split(",") if p.strip()]
                if not raw_parts:
                    self.add_error("dates", "Please provide at least one date in DD/MM/YYYY format.")
                for part in raw_parts:
                    try:
                        dt = datetime.strptime(part, "%d/%m/%Y").date()
                        parsed_dates.add(dt)
                    except ValueError:
                        self.add_error("dates", f"Invalid date format: '{part}'. Please use DD/MM/YYYY (e.g. 05/09/2026).")
                cleaned_data["parsed_dates"] = sorted(list(parsed_dates))
        return cleaned_data

    def save(self, commit=True):
        task = super().save(commit=commit)
        task_type = task.task_type
        parsed_dates = self.cleaned_data.get("parsed_dates", [])

        def save_m2m():
            if task_type == Task.TODAY:
                task.weekday = None
                task.save(update_fields=["weekday"])
                today = timezone.localdate()
                task.date_assignments.exclude(date=today).delete()
                TaskDateAssignment.objects.get_or_create(task=task, date=today)
            elif task_type == Task.DATE:
                task.weekday = None
                task.save(update_fields=["weekday"])
                task.date_assignments.exclude(date__in=parsed_dates).delete()
                for d in parsed_dates:
                    TaskDateAssignment.objects.get_or_create(task=task, date=d)
            elif task_type == Task.WEEKDAY:
                task.date_assignments.all().delete()
            else:
                task.weekday = None
                task.save(update_fields=["weekday"])
                task.date_assignments.all().delete()

        if commit:
            save_m2m()
        else:
            self.save_m2m = save_m2m

        return task

