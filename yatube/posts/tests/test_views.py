import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.cache import cache

from posts.models import Group, Post, User, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug_test',
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа_2',
            slug='slug_test_2',
            description='Тестовое описание_2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group,
            image=uploaded
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        user_2 = User.objects.create_user(username='follower')
        cls.follower_client = Client()
        cls.follower_client.force_login(user_2)
        Follow.objects.create(user=user_2, author=cls.user)

    def setUp(self):
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_index_correct_template(self):
        """URL-адрес использует шаблон posts/index.html."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertTemplateUsed(response, 'posts/index.html')

    def test_index_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': 'slug_test'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': 'auth'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': '1'}): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': '1'}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_correct_context(self):
        """Проверяем страницы в контексте"""
        views_names = {
            'posts:index': None,
            'posts:group_list': {'slug': 'slug_test'},
            'posts:profile': {'username': 'auth'},
            'posts:follow_index': None,
        }
        for url_name, data in views_names.items():
            with self.subTest(url_name=url_name, data=data):
                response = self.follower_client.get(
                    reverse(url_name, kwargs=data))
                self.assertEqual(
                    response.context['page_obj'][0].author, self.post.author)
                self.assertEqual(
                    response.context['page_obj'][0].text, self.post.text)
                self.assertEqual(
                    response.context['page_obj'][0].group, self.group)
                self.assertEqual(
                    response.context['page_obj'][0].image, self.post.image)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(
            response.context.get('post').author, self.post.author)
        self.assertEqual(
            response.context.get('post').text, self.post.text)
        self.assertEqual(
            response.context.get('post').group, self.group)
        self.assertEqual(
            response.context.get('post').image, self.post.image)

    def test_post_not_in_outher_groups(self):
        """Проверяем принадлежность постов к группам"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'slug_test_2'}))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_post_create_and_edit_context(self):
        """тестируем контекст создания и редактирования контекста"""
        views_names = {
            'posts:post_create': None,
            'posts:post_edit': {'post_id': '1'},
        }
        for url_name, data in views_names.items():
            response = self.authorized_client.get(reverse(
                url_name, kwargs=data))

            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
            }
            for field, forms_field in form_fields.items():
                with self.subTest(field=field):
                    form_field = response.context.get('form').fields.get(field)
                    self.assertIsInstance(form_field, forms_field)

    def test_individual_context(self):
        """Тестируем индивидуальные переменные в контекстах"""
        urls_data = (
            ('posts:post_edit', (1,), 'is_edit', True),
            ('posts:profile', ('auth',), 'author', self.user),
            ('posts:group_list', ('slug_test',), 'group', self.group))

        for url_name, url_data, variable_name, exists_data in urls_data:
            with self.subTest(url_name=url_name, url_data=url_data):
                response = self.authorized_client.get(
                    reverse(url_name, args=url_data))
                self.assertEqual(response.context[variable_name], exists_data)

    def test_cache_index(self):
        cache.clear()
        response_1 = self.authorized_client.get(
            reverse('posts:index'))
        Post.objects.create(
            author=self.user,
            text='Тукст для теста кеша',
            group=self.group,
        )
        response_2 = self.authorized_client.get(
            reverse('posts:index'))
        cache.clear()
        response_3 = self.authorized_client.get(
            reverse('posts:index'))

        self.assertEqual(response_1.content, response_2.content)
        self.assertEqual(len(response_3.context['page_obj']), 2)

    def test_cache_index(self):
        """Тестируем использование подписок"""
        follow_count = Follow.objects.count()
        url_list = (
            ('posts:profile_follow', (self.user.username,), 2),
            ('posts:profile_unfollow', (self.user.username,), 1),
        )
        for url_name, url_data, arithmetic_data in url_list:
            with self.subTest(url_name=url_name, url_data=url_data):
                self.follower_client.get(
                    reverse(url_name, args=url_data))
                self.assertEqual(Follow.objects.count(),
                                 follow_count + int(arithmetic_data))

    def test_cache_index(self):
        """Тестируем использование подписок"""
        user_list = (
            (self.follower_client, 1),
            (self.authorized_client, 0)
        )
        for user_name, test_data in user_list:
            with self.subTest(user_name=user_name, test_data=test_data):
                response = (user_name).get(
                    reverse('posts:follow_index'))
            self.assertEqual(len(response.context['page_obj']), test_data)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='test-slug'
        )
        QOANTITY_PAGE_OBJ = 11
        for i in range(QOANTITY_PAGE_OBJ):
            Post.objects.create(
                text=f'{i}',
                author=cls.user,
                group=cls.group
            )
        cls.guest_client = Client()

    def setUp(self):
        cache.clear()

    def test_contains_posts(self):
        """Тестируем пейджинатор"""
        HOW_MANU_POSTS_ON_1 = 10
        HOW_MANU_POSTS_ON_2 = 1
        views_names = {
            'posts:index': None,
            'posts:group_list': {'slug': 'test-slug'},
            'posts:profile': {'username': 'auth'},
        }
        for url_name, data in views_names.items():
            with self.subTest(url_name=url_name, data=data):
                response_1 = self.client.get(
                    reverse(url_name, kwargs=data))
            response_2 = self.client.get(
                reverse(url_name, kwargs=data) + '?page=2')
            self.assertEqual(
                len(response_1.context['page_obj']), HOW_MANU_POSTS_ON_1)
            self.assertEqual(
                len(response_2.context['page_obj']), HOW_MANU_POSTS_ON_2)
