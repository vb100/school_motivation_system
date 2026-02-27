from django.test import TestCase
from django.utils import timezone

from core.models import (
    User,
    StudentProfile,
    TeacherProfile,
    Semester,
    TeacherBudget,
    BonusItem,
    BonusRedemptionRequest,
    PointTransaction,
    GroupPurchase,
    GroupContribution,
)
from core.services import (
    award_points,
    redeem_bonus,
    admin_adjust_points,
    student_balance_points,
    student_reserved_points,
    reserve_group_points,
    confirm_group_purchase,
    withdraw_group_reservation,
    create_bonus_redemption_request,
    confirm_bonus_redemption_request,
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
        self.teacher_user_two = User.objects.create_user(username="teacher2", password="pass", role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(username="student", password="pass", role=User.Role.STUDENT)
        self.admin_user = User.objects.create_user(username="admin", password="pass", role=User.Role.ADMIN)
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher_user, display_name="Mokytojas")
        self.teacher_profile_two = TeacherProfile.objects.create(user=self.teacher_user_two, display_name="Mokytojas 2")
        self.student_profile = StudentProfile.objects.create(user=self.student_user, display_name="Mokinys")
        self.student_user_two = User.objects.create_user(username="student2", password="pass", role=User.Role.STUDENT)
        self.student_profile_two = StudentProfile.objects.create(user=self.student_user_two, display_name="Mokinys 2")
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
        self.points_related_bonus = BonusItem.objects.create(
            title_lt="Papildomas balas",
            description_lt="Patvirtina mokytojas",
            price_points=40,
            max_uses_per_student=1,
            is_active=True,
            category=BonusItem.Category.POINTS_RELATED,
        )
        self.points_related_bonus.assigned_teachers.add(self.teacher_profile)

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

    def test_group_purchase_flow(self) -> None:
        self.budget.allocated_points = 200
        self.budget.save(update_fields=["allocated_points"])
        self.bonus.price_points = 60
        self.bonus.save(update_fields=["price_points"])
        award_points(self.teacher_user, self.student_profile, 60, "Taškai")
        award_points(self.teacher_user, self.student_profile_two, 60, "Taškai")

        reserve_group_points(self.student_user, self.bonus, 30)
        reserve_group_points(self.student_user_two, self.bonus, 30)

        group_purchase = GroupPurchase.objects.get(bonus_item=self.bonus, semester=self.semester)
        self.assertEqual(group_purchase.status, GroupPurchase.Status.AWAITING_CONFIRMATION)

        confirm_group_purchase(self.student_user, self.bonus)
        group_purchase.refresh_from_db()
        self.assertEqual(group_purchase.status, GroupPurchase.Status.AWAITING_CONFIRMATION)

        confirm_group_purchase(self.student_user_two, self.bonus)
        group_purchase.refresh_from_db()
        self.assertEqual(group_purchase.status, GroupPurchase.Status.COMPLETED)
        self.assertEqual(
            PointTransaction.objects.filter(bonus_item=self.bonus, tx_type=PointTransaction.TxType.REDEEM).count(),
            2,
        )

    def test_group_reservation_withdraw_only_single_contributor(self) -> None:
        award_points(self.teacher_user, self.student_profile, 40, "Taškai")
        reserve_group_points(self.student_user, self.bonus, 20)
        withdraw_group_reservation(self.student_user, self.bonus)
        self.assertEqual(GroupContribution.objects.count(), 0)

        reserve_group_points(self.student_user, self.bonus, 10)
        reserve_group_points(self.student_user_two, self.bonus, 10)
        with self.assertRaises(DomainError):
            withdraw_group_reservation(self.student_user, self.bonus)

    def test_points_related_bonus_requires_teacher_confirmation(self) -> None:
        award_points(self.teacher_user, self.student_profile, 80, "Taškai")
        request = create_bonus_redemption_request(
            self.student_user,
            self.points_related_bonus,
            self.teacher_profile.id,
        )
        self.assertEqual(request.status, BonusRedemptionRequest.Status.PENDING)
        self.assertEqual(
            PointTransaction.objects.filter(
                bonus_item=self.points_related_bonus,
                tx_type=PointTransaction.TxType.REDEEM,
            ).count(),
            0,
        )

        with self.assertRaises(DomainError):
            confirm_bonus_redemption_request(self.teacher_user_two, request)

        tx = confirm_bonus_redemption_request(self.teacher_user, request)
        request.refresh_from_db()
        self.assertEqual(request.status, BonusRedemptionRequest.Status.APPROVED)
        self.assertEqual(tx.points_delta, -40)

    def test_points_related_bonus_disables_group_purchase(self) -> None:
        with self.assertRaises(DomainError):
            reserve_group_points(self.student_user, self.points_related_bonus, 10)

    def test_points_related_bonus_requires_assigned_teacher(self) -> None:
        award_points(self.teacher_user, self.student_profile, 80, "Taškai")
        with self.assertRaises(DomainError):
            create_bonus_redemption_request(
                self.student_user,
                self.points_related_bonus,
                self.teacher_profile_two.id,
            )
