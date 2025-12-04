from django.urls import reverse
from rest_framework import status

from blog.factories import CategoryFactory, TagFactory
from blog.models import Category, Tag
from blog.tests.base import BaseAPITestCase


class CategoryAPITest(BaseAPITestCase):
    def test_create_category(self):
        self._authenticate_as_staff()
        url = reverse('blog:category-list')
        data = {'name': 'New Category', 'slug': 'new-category'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(slug='new-category').exists())

    def test_create_nested_category(self):
        self._authenticate_as_staff()
        parent_category = CategoryFactory()
        url = reverse('blog:category-list')
        data = {'name': 'Sub Category', 'slug': 'sub-category', 'parent': parent_category.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(slug='sub-category', parent=parent_category).exists())

    def test_list_categories(self):
        CategoryFactory.create_batch(3)
        url = reverse('blog:category-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


class TagAPITest(BaseAPITestCase):
    def test_create_tag(self):
        self._authenticate_as_staff()
        url = reverse('blog:tag-list')
        data = {'name': 'New Tag', 'slug': 'new-tag'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tag.objects.filter(slug='new-tag').exists())

    def test_list_tags(self):
        TagFactory.create_batch(5)
        url = reverse('blog:tag-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

    def test_tag_list_returns_id(self):
        """
        Ensure the tag list API endpoint returns the tag ID.
        """
        self._authenticate_as_staff()
        tag = TagFactory()
        url = reverse('blog:tag-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data[0])
        self.assertEqual(response.data[0]['id'], tag.id)

    def test_tag_detail_returns_id(self):
        """
        Ensure the tag detail API endpoint returns the tag ID.
        """
        self._authenticate_as_staff()
        tag = TagFactory()
        url = reverse('blog:tag-detail', kwargs={'pk': tag.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['id'], tag.id)
