from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Verification

User = get_user_model()

class VerificationModelTests(TestCase):
    def test_verification_creation(self):
        user = User.objects.create_user(username="testuser", password="password", phone_number="+123")
        verification = Verification.objects.create(user=user, level=1)
        self.assertEqual(verification.user, user)
        self.assertEqual(verification.level, 1)
