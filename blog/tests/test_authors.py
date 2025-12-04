from django.urls import reverse
from rest_framework import status

from blog.factories import AuthorProfileFactory, UserFactory
from blog.models import AuthorProfile
from blog.tests.base import BaseAPITestCase


class AuthorProfileAPITest(BaseAPITestCase):
    def test_update_own_author_profile(self):
        """
        Ensures a user can update their own author profile.
        """
        self._authenticate() # Authenticate as the normal user
        url = reverse('blog:authorprofile-detail', kwargs={'pk': self.author_profile.pk})
        data = {'display_name': 'New Display Name'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.author_profile.refresh_from_db()
        self.assertEqual(self.author_profile.display_name, 'New Display Name')

    def test_cannot_update_other_author_profile(self):
        """
        Ensures a user cannot update another user's author profile.
        """
        self._authenticate() # Authenticate as the normal user
        # Try to update the staff user's profile
        url = reverse('blog:authorprofile-detail', kwargs={'pk': self.staff_author_profile.pk})
        data = {'display_name': 'Should Not Work'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_other_author_profile(self):
        """
        Ensures an admin user can update another user's author profile.
        """
        self._authenticate_as_staff()
        # Try to update the normal user's profile
        url = reverse('blog:authorprofile-detail', kwargs={'pk': self.author_profile.pk})
        data = {'display_name': 'Admin Was Here'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.author_profile.refresh_from_db()
        self.assertEqual(self.author_profile.display_name, 'Admin Was Here')

    def test_list_author_profiles(self):
        """
        Ensures we can list author profiles.
        """
        initial_count = AuthorProfile.objects.count()
        AuthorProfileFactory.create_batch(3)
        url = reverse('blog:authorprofile-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AuthorProfile.objects.count(), initial_count + 3)

    def test_retrieve_author_profile(self):
        """
        Ensures we can retrieve a single author profile.
        """
        author_profile = AuthorProfileFactory()
        url = reverse('blog:authorprofile-detail', kwargs={'pk': author_profile.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], author_profile.display_name)

    def test_update_author_profile(self):
        """
        Ensures we can update an author profile.
        """
        self._authenticate_as_staff()
        author_profile = self.staff_author_profile # Use the staff's own profile
        url = reverse('blog:authorprofile-detail', kwargs={'pk': author_profile.pk})
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
        url = reverse('blog:authorprofile-detail', kwargs={'pk': author_profile.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AuthorProfile.objects.filter(pk=author_profile.pk).exists())
