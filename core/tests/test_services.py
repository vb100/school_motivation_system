from django.test import TestCase
from django.utils import timezone

from core.models import (
    User,
    StudentProfile,
    TeacherProfile,
    Semester,
    TeacherBudget,
    BonusItem,
    PointTransaction,
)
from core.services import (
    award_points,
    redeem_bonus,
    admin_adjust_points,
    student_balance_points,
    DomainError,
)


class ServicesTests(TestCase):
    def setUp(self) -> None:
        self.semester = Semester.objects.create(
            name="2024 Ruduo",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        self.teacher_user = User.objects.create_user(username="teacher", password="pass", role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(username="student", password="pass", role=User.Role.STUDENT)
        self.admin_user = User.objects.create_user(username="admin", password="pass", role=User.Role.ADMIN)
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher_user, display_name="Mokytojas")
        self.student_profile = StudentProfile.objects.create(user=self.student_user, display_name="Mokinys")
        self.budget = TeacherBudget.objects.create(
            teacher_profile=self.teacher_profile,
            semester=self.semester,
            allocated_points=100,
            spent_points=0,
        )
        self.bonus = BonusItem.objects.create(
            title_lt="Nemokamas bilietas",
            description_lt="Bilietas į renginį",
            price_points=30,
            max_uses_per_student=1,
            is_active=True,
        )

    def test_award_points_decreases_budget(self) -> None:
        tx = award_points(self.teacher_user, self.student_profile, 20, "Puikiai!")
        self.budget.refresh_from_db()
        self.assertEqual(tx.points_delta, 20)
        self.assertEqual(self.budget.spent_points, 20)
        balance = student_balance_points(self.student_profile, self.semester)
        self.assertEqual(balance, 20)

    def test_award_points_over_budget_raises(self) -> None:
        with self.assertRaises(DomainError):
            award_points(self.teacher_user, self.student_profile, 200, "Per daug")

    def test_redeem_bonus_enforces_balance_and_limits(self) -> None:
        award_points(self.teacher_user, self.student_profile, 50, "Taškai")
        redeem_bonus(self.student_user, self.bonus)
        balance = student_balance_points(self.student_profile, self.semester)
        self.assertEqual(balance, 20)
        with self.assertRaises(DomainError):
            redeem_bonus(self.student_user, self.bonus)

    def test_admin_adjust_points(self) -> None:
        tx = admin_adjust_points(self.admin_user, self.student_profile, 10, "Korekcija")
        self.assertEqual(tx.tx_type, PointTransaction.TxType.ADMIN_ADJUST)
        balance = student_balance_points(self.student_profile, self.semester)
        self.assertEqual(balance, 10)
