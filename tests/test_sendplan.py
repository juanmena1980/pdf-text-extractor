import unittest
from datetime import date, datetime, timedelta

from sintesis.sendplan import InvalidSendTime, describe_plan, parse_hhmm, plan_send


class SendPlanTest(unittest.TestCase):
    def test_schedules_ten_minutes_before(self):
        edition = date(2026, 9, 29)
        now = datetime(2026, 9, 29, 7, 0)
        plan = plan_send(now, edition, "08:00")
        self.assertFalse(plan.immediate)
        self.assertEqual(plan.send_at, datetime(2026, 9, 29, 7, 50))
        self.assertEqual(plan.official_at, datetime(2026, 9, 29, 8, 0))
        self.assertIn("07:50", describe_plan(plan))
        self.assertIn("10 minutos", describe_plan(plan))

    def test_sends_now_when_the_lead_already_passed(self):
        edition = date(2026, 9, 29)
        now = datetime(2026, 9, 29, 7, 52)
        plan = plan_send(now, edition, "08:00")
        self.assertTrue(plan.immediate)
        self.assertEqual(plan.send_at, now)

    def test_sends_now_at_the_exact_lead(self):
        now = datetime(2026, 9, 29, 7, 50)
        plan = plan_send(now, date(2026, 9, 29), "08:00")
        self.assertTrue(plan.immediate)

    def test_sends_now_after_the_official_time(self):
        now = datetime(2026, 9, 29, 8, 5)
        plan = plan_send(now, date(2026, 9, 29), "8:00")
        self.assertTrue(plan.immediate)
        self.assertEqual(plan.send_at, now)
        self.assertIn("ya es la hora", describe_plan(plan))

    def test_lead_can_cross_midnight(self):
        now = datetime(2026, 9, 28, 23, 50)
        plan = plan_send(now, date(2026, 9, 29), "00:05")
        self.assertFalse(plan.immediate)
        self.assertEqual(plan.send_at, datetime(2026, 9, 28, 23, 55))
        self.assertEqual(plan.official_at, datetime(2026, 9, 29, 0, 5))

    def test_rejects_bad_clock(self):
        with self.assertRaises(InvalidSendTime):
            parse_hhmm("25:00")
        self.assertEqual(parse_hhmm("8:05").minute, 5)

    def test_truncates_microseconds_for_immediate_send(self):
        now = datetime(2026, 9, 29, 9, 0, 1, 40)
        plan = plan_send(now, date(2026, 9, 29), "08:00")
        self.assertEqual(plan.send_at, now.replace(microsecond=0))
        self.assertEqual(plan.send_at - now.replace(microsecond=0), timedelta())


if __name__ == "__main__":
    unittest.main()
