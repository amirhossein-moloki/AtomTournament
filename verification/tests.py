from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Verification
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from PIL import Image
from io import BytesIO

User = get_user_model()


class VerificationModelTests(TestCase):
    def test_verification_creation(self):
        user = User.objects.create_user(
            username="testuser", password="password", phone_number="+123"
        )
        verification = Verification.objects.create(user=user, level=1)
        self.assertEqual(verification.user, user)
        self.assertEqual(verification.level, 1)


class VerificationViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+12345"
        )
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+54321"
        )
        self.level2_url = "/api/verification/submit_level2/"
        self.level3_url = "/api/verification/submit_level3/"
        self.admin_url_template = "/api/verification/{}/approve/"

    def _generate_dummy_image(self, name="test.png"):
        file = BytesIO()
        image = Image.new("RGB", (10, 10), "white")
        image.save(file, "png")
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(name, file.read(), content_type="image/png")

    def test_submit_level2_verification_unauthenticated(self):
        response = self.client.post(self.level2_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_level2_verification_success(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "id_card_image": self._generate_dummy_image("id_card.png"),
            "selfie_image": self._generate_dummy_image("selfie.png"),
        }
        response = self.client.post(self.level2_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        verification = Verification.objects.get(user=self.user)
        self.assertEqual(verification.level, 2)
        self.assertFalse(verification.is_verified)
        self.assertIsNotNone(verification.id_card_image)

    def test_submit_level2_missing_images_fails(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.level2_url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resubmit_level2_when_already_verified_fails(self):
        Verification.objects.create(user=self.user, level=2, is_verified=True)
        self.client.force_authenticate(user=self.user)
        data = {
            "id_card_image": self._generate_dummy_image("id_card.png"),
            "selfie_image": self._generate_dummy_image("selfie.png"),
        }
        response = self.client.post(self.level2_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_approve_verification_success(self):
        verification = Verification.objects.create(user=self.user, level=2)
        self.client.force_authenticate(user=self.admin_user)
        url = self.admin_url_template.format(verification.pk)
        data = {"is_verified": True}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)

    def test_admin_reject_verification(self):
        verification = Verification.objects.create(
            user=self.user, level=2, is_verified=True
        )
        self.client.force_authenticate(user=self.admin_user)
        url = self.admin_url_template.format(verification.pk)
        data = {"is_verified": False}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        verification.refresh_from_db()
        self.assertFalse(verification.is_verified)

    def test_non_admin_cannot_update_verification(self):
        verification = Verification.objects.create(user=self.user, level=2)
        self.client.force_authenticate(user=self.user)
        url = self.admin_url_template.format(verification.pk)
        data = {"is_verified": True}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submit_level3_not_level2_verified_fails(self):
        self.client.force_authenticate(user=self.user)
        data = {"video": self._generate_dummy_image("video.mp4")}
        response = self.client.post(self.level3_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_level3_success(self):
        Verification.objects.create(user=self.user, level=2, is_verified=True)
        self.client.force_authenticate(user=self.user)
        data = {"video": self._generate_dummy_image("video.mp4")}
        response = self.client.post(self.level3_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        verification = Verification.objects.get(user=self.user)
        self.assertEqual(verification.level, 3)
        self.assertFalse(verification.is_verified)
        self.assertIsNotNone(verification.video)

    def test_submit_level3_missing_video_fails(self):
        Verification.objects.create(user=self.user, level=2, is_verified=True)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.level3_url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def tearDown(self):
        # Clean up created media files
        for verification in Verification.objects.all():
            if verification.id_card_image:
                if os.path.exists(verification.id_card_image.path):
                    os.remove(verification.id_card_image.path)
            if verification.selfie_image:
                if os.path.exists(verification.selfie_image.path):
                    os.remove(verification.selfie_image.path)
            if verification.video:
                if os.path.exists(verification.video.path):
                    os.remove(verification.video.path)
