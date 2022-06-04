from http import HTTPStatus
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from posts.models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug_test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.client1 = User.objects.create_user(username='not_auth')
        cls.authorized_client1 = Client()
        cls.authorized_client1.force_login(cls.client1)

    def setUp(self):
        cache.clear()

    def test_authorized_client_url(self):
        """Тестируем функционал авторизованного клиента"""
        test_urls = ('/create/', '/posts/1/edit/')
        for address in test_urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_not_authorized_client_url(self):
        """Тестируем функционал не авторизованного клиента"""
        test_urls = {
            '/': HTTPStatus.OK,
            '/group/slug_test/': HTTPStatus.OK,
            '/profile/auth/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/zdrgzdfhxfghstgh/': HTTPStatus.NOT_FOUND,
            'posts/<int:post_id>/comment/': HTTPStatus.NOT_FOUND
        }
        for address, repons in test_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, repons)

    def test_not_authorized_client_redirect(self):
        """Тестируем редиректы анонима."""
        test_urls = ['/create/', '/posts/1/edit/']
        for address in test_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(
                    response, f'/auth/login/?next={address}')

    def test_authorized_client_redirect(self):
        """Ткст попытки редактирования поста не автором"""

        response = self.authorized_client1.get('/posts/1/edit/', follow=True)
        self.assertRedirects(
            response, (reverse('posts:post_detail',
                               kwargs={'post_id': '1'})))

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/slug_test/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)


class StaticURLTests(TestCase):
    """Сестируем пейджинатор"""
    def test_homepage(self):
        guest_client = Client()
        response = guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
