from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Стоит сделать подлиннее текст, чтобы было видно,'
                 ' что действительно корректно все работает',
        )

    def test_model_post(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        NUMBER_OF_LETTERS = 15
        post_obj = self.post
        expected_text = post_obj.text[:NUMBER_OF_LETTERS]
        self.assertEqual(str(post_obj),
                         expected_text,
                         'slomalsa __str__ posta')


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug_test',
            description='Тестовое описание',
        )

    def test_model_group(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        clas_obj = self.group
        expected_title = clas_obj.title
        self.assertEqual(str(clas_obj),
                         expected_title,
                         'slomalsa __str__ group')
