from datetime import date, timedelta
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import (
    Countdown,
    DisciplineSettings,
    Goal,
    MotivationQuote,
    Task,
    TaskCompletion,
    TaskDateAssignment,
)
from .forms import TaskForm
from .views import get_day_type, get_tasks_for_day, is_task_available_on


class TaskAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = Client()
        self.client.force_login(self.user)

        # 2026-09-07 is Monday (weekday 0)
        # 2026-09-08 is Tuesday (weekday 1)
        # 2026-09-09 is Wednesday (weekday 2)
        # 2026-09-10 is Thursday (weekday 3)
        # 2026-09-11 is Friday (weekday 4)
        # 2026-09-12 is Saturday (weekday 5)
        # 2026-09-13 is Sunday (weekday 6)
        self.monday = date(2026, 9, 7)
        self.tuesday = date(2026, 9, 8)
        self.wednesday = date(2026, 9, 9)
        self.thursday = date(2026, 9, 10)
        self.friday = date(2026, 9, 11)
        self.saturday = date(2026, 9, 12)
        self.sunday = date(2026, 9, 13)

    # 1. Permanent task appears Monday
    def test_01_permanent_task_appears_monday(self):
        task = Task.objects.create(title="Permanent Task", task_type=Task.PERMANENT, order=1)
        self.assertTrue(task.is_available_on(self.monday))
        pending, completed = get_tasks_for_day("odd", self.monday)
        self.assertIn(task, pending)

    # 2. Permanent task does not appear Sunday
    def test_02_permanent_task_does_not_appear_sunday(self):
        task = Task.objects.create(title="Permanent Task", task_type=Task.PERMANENT, order=1)
        self.assertFalse(task.is_available_on(self.sunday))
        pending, completed = get_tasks_for_day("holiday", self.sunday)
        self.assertNotIn(task, pending)

    # 3. Odd task appears Monday
    def test_03_odd_task_appears_monday(self):
        task = Task.objects.create(title="Odd Task", task_type=Task.ODD, order=1)
        self.assertTrue(task.is_available_on(self.monday))
        pending, completed = get_tasks_for_day("odd", self.monday)
        self.assertIn(task, pending)

    # 4. Odd task does not appear Tuesday
    def test_04_odd_task_does_not_appear_tuesday(self):
        task = Task.objects.create(title="Odd Task", task_type=Task.ODD, order=1)
        self.assertFalse(task.is_available_on(self.tuesday))
        pending, completed = get_tasks_for_day("even", self.tuesday)
        self.assertNotIn(task, pending)

    # 5. Even task appears Tuesday
    def test_05_even_task_appears_tuesday(self):
        task = Task.objects.create(title="Even Task", task_type=Task.EVEN, order=1)
        self.assertTrue(task.is_available_on(self.tuesday))
        pending, completed = get_tasks_for_day("even", self.tuesday)
        self.assertIn(task, pending)

    # 6. Today task appears on its assigned date
    def test_06_today_task_appears_on_assigned_date(self):
        task = Task.objects.create(title="Today Task", task_type=Task.TODAY, order=1)
        TaskDateAssignment.objects.create(task=task, date=self.monday)
        self.assertTrue(task.is_available_on(self.monday))
        pending, _ = get_tasks_for_day("odd", self.monday)
        self.assertIn(task, pending)

    # 7. Today task does not appear on the following day
    def test_07_today_task_does_not_appear_on_following_day(self):
        task = Task.objects.create(title="Today Task", task_type=Task.TODAY, order=1)
        TaskDateAssignment.objects.create(task=task, date=self.monday)
        self.assertFalse(task.is_available_on(self.tuesday))
        pending, _ = get_tasks_for_day("even", self.tuesday)
        self.assertNotIn(task, pending)

    # 8. Specific Monday task appears Monday
    def test_08_specific_monday_task_appears_monday(self):
        task = Task.objects.create(title="Monday Task", task_type=Task.WEEKDAY, weekday=0, order=1)
        self.assertTrue(task.is_available_on(self.monday))
        pending, _ = get_tasks_for_day("odd", self.monday)
        self.assertIn(task, pending)

    # 9. Specific Monday task does not appear Tuesday
    def test_09_specific_monday_task_does_not_appear_tuesday(self):
        task = Task.objects.create(title="Monday Task", task_type=Task.WEEKDAY, weekday=0, order=1)
        self.assertFalse(task.is_available_on(self.tuesday))
        pending, _ = get_tasks_for_day("even", self.tuesday)
        self.assertNotIn(task, pending)

    # 10. Specific Sunday task appears Sunday
    def test_10_specific_sunday_task_appears_sunday(self):
        task = Task.objects.create(title="Sunday Task", task_type=Task.WEEKDAY, weekday=6, order=1)
        self.assertTrue(task.is_available_on(self.sunday))
        pending, _ = get_tasks_for_day("holiday", self.sunday)
        self.assertIn(task, pending)

    # 11. Particular-date task appears on matching date
    def test_11_particular_date_task_appears_on_matching_date(self):
        task = Task.objects.create(title="Particular Date Task", task_type=Task.DATE, order=1)
        target = date(2026, 9, 20)
        TaskDateAssignment.objects.create(task=task, date=target)
        self.assertTrue(task.is_available_on(target))
        pending, _ = get_tasks_for_day("holiday", target)
        self.assertIn(task, pending)

    # 12. Particular-date task does not appear on non-matching date
    def test_12_particular_date_task_does_not_appear_on_non_matching_date(self):
        task = Task.objects.create(title="Particular Date Task", task_type=Task.DATE, order=1)
        target = date(2026, 9, 20)
        TaskDateAssignment.objects.create(task=task, date=target)
        other_date = date(2026, 9, 21)
        self.assertFalse(task.is_available_on(other_date))
        pending, _ = get_tasks_for_day("odd", other_date)
        self.assertNotIn(task, pending)

    # 13. Multiple particular dates work
    def test_13_multiple_particular_dates_work(self):
        task = Task.objects.create(title="Multi Date Task", task_type=Task.DATE, order=1)
        d1 = date(2026, 9, 5)
        d2 = date(2026, 9, 12)
        d3 = date(2026, 9, 20)
        TaskDateAssignment.objects.create(task=task, date=d1)
        TaskDateAssignment.objects.create(task=task, date=d2)
        TaskDateAssignment.objects.create(task=task, date=d3)

        self.assertTrue(task.is_available_on(d1))
        self.assertTrue(task.is_available_on(d2))
        self.assertTrue(task.is_available_on(d3))
        self.assertFalse(task.is_available_on(date(2026, 9, 6)))

    # 14. Duplicate dates are handled
    def test_14_duplicate_dates_handled_in_form(self):
        form_data = {
            "title": "Date Task",
            "description": "Desc",
            "task_type": Task.DATE,
            "dates": "05/09/2026, 05/09/2026, 12/09/2026",
            "order": 1,
            "is_active": True,
        }
        form = TaskForm(data=form_data)
        self.assertTrue(form.is_valid())
        task = form.save()
        self.assertEqual(task.date_assignments.count(), 2)

    # 15. Sunday-specific tasks work
    def test_15_sunday_specific_tasks_work(self):
        t_today = Task.objects.create(title="Sunday Today Task", task_type=Task.TODAY, order=1)
        TaskDateAssignment.objects.create(task=t_today, date=self.sunday)

        t_weekday = Task.objects.create(title="Sunday Weekday Task", task_type=Task.WEEKDAY, weekday=6, order=2)

        t_date = Task.objects.create(title="Sunday Particular Date Task", task_type=Task.DATE, order=3)
        TaskDateAssignment.objects.create(task=t_date, date=self.sunday)

        t_perm = Task.objects.create(title="Perm Task", task_type=Task.PERMANENT, order=4)

        pending, _ = get_tasks_for_day("holiday", self.sunday)
        self.assertIn(t_today, pending)
        self.assertIn(t_weekday, pending)
        self.assertIn(t_date, pending)
        self.assertNotIn(t_perm, pending)

    # 16. Unavailable tasks cannot be completed
    def test_16_unavailable_tasks_cannot_be_completed(self):
        # Odd task on Tuesday is unavailable
        task = Task.objects.create(title="Odd Task", task_type=Task.ODD, order=1)
        today = timezone.localdate()
        # Ensure task is not available today by setting a date assignment or task_type
        if task.is_available_on(today):
            task.task_type = Task.EVEN if task.task_type == Task.ODD else Task.ODD
            task.save()

        # Try completing it
        response = self.client.post(reverse("complete_task", args=[task.id]))
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertEqual(json_data.get("status"), "error")
        self.assertEqual(json_data.get("message"), "This task is not available today.")

    # 17. Completion remains unique per task/date
    def test_17_completion_remains_unique_per_task_date(self):
        task = Task.objects.create(title="Perm Task", task_type=Task.PERMANENT, order=1)
        d = date(2026, 9, 7)
        c1, created1 = TaskCompletion.objects.get_or_create(task=task, date=d)
        c2, created2 = TaskCompletion.objects.get_or_create(task=task, date=d)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(TaskCompletion.objects.filter(task=task, date=d).count(), 1)

    # 18. History includes all assignment types
    def test_18_history_includes_all_assignment_types(self):
        # Create one task of each type
        t_perm = Task.objects.create(title="Perm", task_type=Task.PERMANENT, order=1)
        t_odd = Task.objects.create(title="Odd", task_type=Task.ODD, order=2)
        t_even = Task.objects.create(title="Even", task_type=Task.EVEN, order=3)
        t_today = Task.objects.create(title="Today", task_type=Task.TODAY, order=4)
        TaskDateAssignment.objects.create(task=t_today, date=self.monday)
        t_weekday = Task.objects.create(title="Weekday", task_type=Task.WEEKDAY, weekday=0, order=5)
        t_date = Task.objects.create(title="Date", task_type=Task.DATE, order=6)
        TaskDateAssignment.objects.create(task=t_date, date=self.monday)

        # Complete permanent and weekday task on Monday
        TaskCompletion.objects.create(task=t_perm, date=self.monday)
        TaskCompletion.objects.create(task=t_weekday, date=self.monday)

        response = self.client.get(reverse("history"))
        self.assertEqual(response.status_code, 200)
        history_list = response.context["history"]
        monday_entry = next((e for e in history_list if e["date"] == self.monday), None)
        self.assertIsNotNone(monday_entry)
        self.assertEqual(monday_entry["completed"], 2)
        # On Monday: Perm (1), Odd (1), Today (1), Weekday=0 (1), Date (1) -> Total 5
        self.assertEqual(monday_entry["total"], 5)

    # 19. Existing permanent/odd/even tasks continue working
    def test_19_existing_permanent_odd_even_tasks_work(self):
        t1 = Task.objects.create(title="Perm", task_type="permanent", order=1)
        t2 = Task.objects.create(title="Odd", task_type="odd", order=2)
        t3 = Task.objects.create(title="Even", task_type="even", order=3)

        # Mon
        p, _ = get_tasks_for_day("odd", self.monday)
        self.assertIn(t1, p)
        self.assertIn(t2, p)
        self.assertNotIn(t3, p)

        # Tue
        p, _ = get_tasks_for_day("even", self.tuesday)
        self.assertIn(t1, p)
        self.assertNotIn(t2, p)
        self.assertIn(t3, p)


class HomepageContentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = Client()
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    # 20. Countdown is loaded from database
    def test_20_countdown_loaded_from_database(self):
        c = Countdown.objects.create(
            title="EXAM COUNTDOWN",
            target_date=self.today + timedelta(days=10),
            subtitle="Focus on preparation",
            is_active=True,
            order=1,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EXAM COUNTDOWN")
        self.assertContains(response, "Focus on preparation")

    # 21. Future countdown calculates correctly
    def test_21_future_countdown_calculates_correctly(self):
        c = Countdown.objects.create(
            title="FUTURE EVENT",
            target_date=self.today + timedelta(days=5),
            is_active=True,
            order=1,
        )
        info = c.get_countdown_info(self.today)
        self.assertEqual(info["status"], "countdown")
        self.assertEqual(info["days_remaining"], 5)

    # 22. Today's countdown returns correct status
    def test_22_today_countdown_returns_correct_status(self):
        c = Countdown.objects.create(
            title="TODAY EVENT",
            target_date=self.today,
            is_active=True,
            order=1,
        )
        info = c.get_countdown_info(self.today)
        self.assertEqual(info["status"], "today")
        self.assertEqual(info["days_remaining"], 0)

    # 23. Passed countdown returns correct status
    def test_23_passed_countdown_returns_correct_status(self):
        c = Countdown.objects.create(
            title="PASSED EVENT",
            target_date=self.today - timedelta(days=3),
            is_active=True,
            order=1,
        )
        info = c.get_countdown_info(self.today)
        self.assertEqual(info["status"], "passed")
        self.assertEqual(info["days_remaining"], 0)

    # 24. Multiple countdowns work
    def test_24_multiple_countdowns_work(self):
        c1 = Countdown.objects.create(
            title="EVENT 1",
            target_date=self.today + timedelta(days=10),
            order=1,
            is_active=True,
        )
        c2 = Countdown.objects.create(
            title="EVENT 2",
            target_date=self.today + timedelta(days=20),
            order=2,
            is_active=True,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EVENT 1")
        self.assertContains(response, "EVENT 2")
        self.assertEqual(len(response.context["countdowns"]), 2)

    # 25. Inactive countdowns are hidden
    def test_25_inactive_countdowns_hidden(self):
        c = Countdown.objects.create(
            title="HIDDEN EVENT",
            target_date=self.today + timedelta(days=10),
            is_active=False,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "HIDDEN EVENT")

    # 26. Changing countdown target in Admin changes homepage behavior without code changes
    def test_26_changing_countdown_target_changes_homepage(self):
        c = Countdown.objects.create(
            title="DYNAMIC TARGET",
            target_date=self.today + timedelta(days=15),
            is_active=True,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "15")

        # Update target
        c.target_date = self.today + timedelta(days=7)
        c.save()

        response2 = self.client.get(reverse("home"))
        self.assertContains(response2, "7")

    # 27. Active motivation quote appears
    def test_27_active_motivation_quote_appears(self):
        quote = MotivationQuote.objects.create(
            quote="Consistency is the key to mastery.",
            is_active=True,
            order=1,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Consistency is the key to mastery.")

    # 28. Inactive motivation quote does not appear
    def test_28_inactive_motivation_quote_does_not_appear(self):
        quote = MotivationQuote.objects.create(
            quote="This quote is hidden.",
            is_active=False,
            order=1,
        )
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "This quote is hidden.")

    # 29. Active goals appear
    def test_29_active_goals_appear(self):
        goal = Goal.objects.create(
            icon="🎯",
            title="Read 20 pages",
            description="Daily reading habit",
            is_active=True,
            order=1,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Read 20 pages")
        self.assertContains(response, "Daily reading habit")
        self.assertContains(response, "🎯")

    # 30. Inactive goals do not appear
    def test_30_inactive_goals_do_not_appear(self):
        goal = Goal.objects.create(
            icon="❌",
            title="Inactive Goal",
            is_active=False,
            order=1,
        )
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Inactive Goal")

    # 31. Goal ordering works
    def test_31_goal_ordering_works(self):
        g2 = Goal.objects.create(title="Second Goal", order=2, is_active=True)
        g1 = Goal.objects.create(title="First Goal", order=1, is_active=True)
        response = self.client.get(reverse("home"))
        goals_in_context = list(response.context["goals"])
        self.assertEqual(goals_in_context, [g1, g2])

    # 32. Homepage does not crash if there are no countdowns
    def test_32_homepage_does_not_crash_without_countdowns(self):
        Countdown.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    # 33. Homepage does not crash if there are no quotes
    def test_33_homepage_does_not_crash_without_quotes(self):
        MotivationQuote.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    # 34. Homepage does not crash if there are no goals
    def test_34_homepage_does_not_crash_without_goals(self):
        Goal.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    # 35. Final Countdown renders at the bottom
    def test_35_final_countdown_renders_at_bottom(self):
        Countdown.objects.create(
            title="FINAL COUNTDOWN",
            target_date=date(2026, 12, 31),
            subtitle="Yearly Target",
            is_final=True,
            is_active=True,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FINAL COUNTDOWN")
        self.assertContains(response, "Yearly Target")
        self.assertContains(response, "DAYS LEFT")


class TimeSlotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = Client()
        self.client.force_login(self.user)

    def test_time_slot_helper_morning(self):
        from datetime import datetime
        from tasks.views import get_current_time_slot
        dt = datetime(2026, 9, 7, 7, 30)  # 7:30 AM
        self.assertEqual(get_current_time_slot(dt), "morning")

    def test_time_slot_helper_afternoon(self):
        from datetime import datetime
        from tasks.views import get_current_time_slot
        dt = datetime(2026, 9, 7, 14, 0)  # 2:00 PM
        self.assertEqual(get_current_time_slot(dt), "afternoon")

    def test_time_slot_helper_evening(self):
        from datetime import datetime
        from tasks.views import get_current_time_slot
        dt = datetime(2026, 9, 7, 20, 15)  # 8:15 PM
        self.assertEqual(get_current_time_slot(dt), "evening")

    def test_task_time_slot_persistence_and_form(self):
        form_data = {
            "title": "Morning Routine",
            "description": "Meditate and exercise",
            "task_type": Task.PERMANENT,
            "time_slot": Task.MORNING,
            "order": 1,
            "is_active": True,
        }
        form = TaskForm(data=form_data)
        self.assertTrue(form.is_valid())
        task = form.save()
        self.assertEqual(task.time_slot, Task.MORNING)
        self.assertEqual(task.get_time_slot_icon(), "🌅")
        self.assertEqual(task.get_time_slot_short_label(), "Morning")

    def test_home_page_includes_time_slot_tabs(self):
        t1 = Task.objects.create(title="Morning Meditation", task_type=Task.PERMANENT, time_slot=Task.MORNING, order=1)
        t2 = Task.objects.create(title="Afternoon Deep Work", task_type=Task.PERMANENT, time_slot=Task.AFTERNOON, order=2)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("current_time_slot", response.context)
        self.assertContains(response, 'data-time-slot="morning"')
        self.assertContains(response, 'data-time-slot="afternoon"')
        self.assertContains(response, "ACTIVE NOW")
        self.assertContains(response, "All Tasks")

