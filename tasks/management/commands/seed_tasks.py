from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import (
    Countdown,
    DisciplineSettings,
    Goal,
    MotivationQuote,
    Task,
)


PERMANENT_TASKS = [
    (1, "Give 30 min to brand building",
         "Work on growing your personal brand for 30 focused minutes."),
    (2, "Give 30 min to Learning 1 — Write 3 scripts",
         "Spend 30 minutes on learning and write 3 short scripts."),
    (3, "Analysis 3 scripts S1",
         "Analyse 3 scripts — Session 1."),
    (4, "Analysis 3 scripts S2",
         "Analyse 3 scripts — Session 2."),
    (5, "Learn English",
         "Practice English — reading, writing, or speaking for at least 20 minutes."),
    (6, "Call and mail to potential client",
         "Reach out to at least one potential client via call or email."),
]

ODD_DAY_TASKS = [
    (7,  "Final new topic — Part 1",   "Explore and research a new topic, Part 1."),
    (8,  "Final new topic — Part 2",   "Continue and finalise the new topic, Part 2."),
    (9,  "Explore and final 3 scripts","Find, review, and finalise 3 scripts."),
    (10, "Now analysis each one of this", "Deeply analyse each of the 3 scripts you finalised."),
]

EVEN_DAY_TASKS = [
    (7,  "Write a final hook",     "Write a compelling hook for your content."),
    (8,  "Edit that hook",         "Refine and polish the hook you wrote."),
    (9,  "Final script",           "Write the complete final script."),
    (10, "Analysis and make avatar", "Analyse the script and create/refine the avatar."),
]


class Command(BaseCommand):
    help = "Seeds the database with default tasks and initial configuration."

    def handle(self, *args, **kwargs):
        created_count = 0

        for order, title, desc in PERMANENT_TASKS:
            _, created = Task.objects.get_or_create(
                title=title,
                task_type=Task.PERMANENT,
                defaults={"description": desc, "order": order, "is_active": True},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created [Permanent] #{order}: {title}")

        for order, title, desc in ODD_DAY_TASKS:
            _, created = Task.objects.get_or_create(
                title=title,
                task_type=Task.ODD,
                defaults={"description": desc, "order": order, "is_active": True},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created [Odd]       #{order}: {title}")

        for order, title, desc in EVEN_DAY_TASKS:
            _, created = Task.objects.get_or_create(
                title=title,
                task_type=Task.EVEN,
                defaults={"description": desc, "order": order, "is_active": True},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created [Even]      #{order}: {title}")

        # Ensure DisciplineSettings exists
        DisciplineSettings.get_settings()

        if created_count == 0:
            self.stdout.write(self.style.WARNING("No new tasks created (they may already exist)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone! Created {created_count} tasks."))

