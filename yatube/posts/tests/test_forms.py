import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.conf import settings

from posts.models import Post, Group, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug_test',
            description='Тестовое описание',
        )
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group,
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.guest_client = Client()

        cls.client1 = User.objects.create_user(username='not_auth')
        cls.authorized_client_1 = Client()
        cls.authorized_client_1.force_login(cls.client1)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_create_post(self):
        """Проверяем создание поста"""
        post_count = Post.objects.count()
        group_test = self.group.pk
        text = 'Введите текст поста'
        uploaded = SimpleUploadedFile(
            name='create_post.gif',
            content=self.small_gif,
            content_type='image/gif')
        form_data = {
            'text': text,
            'group': group_test,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(text=text,
                                group=group_test,
                                author=self.post.author,
                                image='posts/create_post.gif',
                                ).exists())

    def test_edit_post(self):
        """проверяет работоспособность формы редактора поста"""
        data_group = self.group.pk
        text = 'Тест текст'
        uploaded = SimpleUploadedFile(
            name='edit_post.gif',
            content=self.small_gif,
            content_type='image/gif')

        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': '1'}),
            data={'text': text,
                  'group': data_group,
                  'image': uploaded,
                  },
            follow=True
        )
        self.assertTrue(Post.objects.filter(pk=1,
                                            text=text,
                                            group=data_group,
                                            pub_date=self.post.pub_date,
                                            author=self.post.author,
                                            image='posts/edit_post.gif',
                                            ).exists())

    def test_post_edit_client(self):
        """проверяет доступ к форме редактирования поста"""
        text = 'test text POST'
        post_count = Post.objects.count()
        data_date = self.post.pub_date
        data_text = self.post.text
        data_author = self.post.author
        data_group = self.post.group
        test_list = {self.authorized_client_1: '/posts/1/',
                     self.guest_client: '/auth/login/?next=/posts/1/edit/'}
        for address, rediirects in test_list.items():
            with self.subTest(address=address):
                response = address.post(
                    reverse('posts:post_edit', kwargs={'post_id': '1'}),
                    data={'text': text,
                          'group': data_group},
                    follow=True
                )
                self.assertEqual(Post.objects.count(), post_count)
                self.assertRedirects(response, rediirects)
                self.assertTrue(Post.objects.filter(author=data_author,
                                                    text=data_text,
                                                    group=data_group,
                                                    pub_date=data_date,
                                                    ).exists())

    def test_post_create_with_guest_client(self):
        """Тест доступа для анонима"""
        post_count = Post.objects.count()
        text = 'Введите текст поста'
        form_data = {
            'text': text,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_comment_with_client(self):
        """Тест доступа к комментированию для анонима"""
        comment_count = Comment.objects.count()
        text = 'Введите текст поста'
        form_data = {
            'text': text,
            'author': self.user,
            'post': self.post
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), comment_count + 1)
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.pk,)))
