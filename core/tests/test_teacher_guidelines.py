from django.test import TestCase
from django.urls import reverse

from core.models import TeacherProfile, User


class TeacherGuidelinesViewTests(TestCase):
    def setUp(self) -> None:
        self.teacher_user = User.objects.create_user(
            username="teacher_guidelines",
            password="pass",
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=self.teacher_user, display_name="Mokytojas")

        self.student_user = User.objects.create_user(
            username="student_guidelines",
            password="pass",
            role=User.Role.STUDENT,
        )

    def test_teacher_can_open_guidelines_page(self) -> None:
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse("teacher_guidelines"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Taškų skyrimo gairės")

    def test_student_is_redirected_from_guidelines_page(self) -> None:
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("teacher_guidelines"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("home"))
