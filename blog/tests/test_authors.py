from django.urls import reverse
from rest_framework import status

from blog.factories import AuthorProfileFactory, UserFactory
from blog.models import AuthorProfile
from blog.tests.base import BaseAPITestCase


class AuthorProfileAPITest(BaseAPITestCase):
    def test_create_author_profile(self):
        """
        Ensures we can create a new author profile.
        """
        self._authenticate_as_staff()
        user = UserFactory()
        url = reverse('authorprofile-list')
        data = {
            'user': user.id,
            'display_name': 'Test Author',
            'bio': 'A test bio.'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuthorProfile.objects.count(), 3)
        self.assertEqual(AuthorProfile.objects.latest('user_id').display_name, 'Test Author')

    def test_list_author_profiles(self):
        """
        Ensures we can list author profiles.
        """
        AuthorProfileFactory.create_batch(3)
        url = reverse('authorprofile-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

    def test_retrieve_author_profile(self):
        """
        Ensures we can retrieve a single author profile.
        """
        author_profile = AuthorProfileFactory()
        url = reverse('authorprofile-detail', kwargs={'pk': author_profile.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], author_profile.display_name)

    def test_update_author_profile(self):
        """
        Ensures we can update an author profile.
        """
        self._authenticate_as_staff()
        author_profile = self.staff_author_profile # Use the staff's own profile
        url = reverse('authorprofile-detail', kwargs={'pk': author_profile.pk})
        data = {'display_name': 'Updated Name'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        author_profile.refresh_from_db()
        self.assertEqual(author_profile.display_name, 'Updated Name')

    def test_delete_author_profile(self):
        """
        Ensures we can delete an author profile.
        """
        self._authenticate_as_staff()
        author_profile = self.staff_author_profile # Use the staff's own profile
        url = reverse('authorprofile-detail', kwargs={'pk': author_profile.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AuthorProfile.objects.filter(pk=author_profile.pk).exists())
