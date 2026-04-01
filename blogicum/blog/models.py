from django.db import models
from django.contrib.auth import get_user_model

from blog.constants import (MAX_LENGTH_FOR_CHAR_FIELDS,
                            MAX_LENGTH_FOR_STR_METHODS)

User = get_user_model()


class BaseModel(models.Model):
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано',
        help_text=('Снимите галочку, '
                   'чтобы скрыть публикацию.')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )

    class Meta:
        abstract = True


class Location(BaseModel):
    name = models.CharField(
        max_length=MAX_LENGTH_FOR_CHAR_FIELDS,
        verbose_name='Название места'
    )

    class Meta:
        verbose_name = 'местоположение'
        verbose_name_plural = 'Местоположения'

    def __str__(self):
        return self.name[:MAX_LENGTH_FOR_STR_METHODS]


class Category(BaseModel):
    title = models.CharField(
        max_length=MAX_LENGTH_FOR_CHAR_FIELDS,
        verbose_name='Заголовок'
    )
    description = models.TextField(verbose_name='Описание')
    slug = models.SlugField(
        unique=True,
        verbose_name='Идентификатор',
        help_text=('Идентификатор страницы для URL; '
                   'разрешены символы латиницы, цифры, '
                   'дефис и подчёркивание.')
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.title[:MAX_LENGTH_FOR_STR_METHODS]


class Post(BaseModel):
    title = models.CharField(
        max_length=MAX_LENGTH_FOR_CHAR_FIELDS,
        verbose_name='Заголовок'
    )
    text = models.TextField(verbose_name='Текст')
    pub_date = models.DateTimeField(
        verbose_name='Дата и время публикации',
        help_text=('Если установить дату и время'
                   ' в будущем — можно делать'
                   ' отложенные публикации.')
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name='Автор публикации',
    )
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL,
        null=True, verbose_name='Местоположение',
        blank=True,
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, verbose_name='Категория',
    )
    image = models.ImageField('Фото', blank=True)

    class Meta:
        verbose_name = 'публикация'
        verbose_name_plural = 'Публикации'
        default_related_name = 'posts'

    def __str__(self):
        return self.title[:MAX_LENGTH_FOR_STR_METHODS]


class Comments(models.Model):
    text = models.TextField(verbose_name='Текст комментария')
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Пост',
    )
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name="Когда создано")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               verbose_name="Автор")

    class Meta:
        ordering = ('created_at',)
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'
        default_related_name = 'comments'

    def __str__(self):
        return self.title[:MAX_LENGTH_FOR_STR_METHODS]
