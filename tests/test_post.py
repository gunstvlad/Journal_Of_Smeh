import datetime
import random
import re
from contextlib import contextmanager
from http import HTTPStatus
from typing import List, Tuple, Type

import django.test.client
import pytest
import pytz
from django.db.models import DateTimeField, ImageField, Model
from django.forms import BaseForm
from django.http import HttpResponse
from django.utils import timezone

from adapters.post import PostModelAdapter
from blogicum.blog.models import Post
from conftest import (
    KeyVal,
    _TestModelAttrs,
    get_create_a_post_get_response_safely,
    get_get_response_safely,
)
from fixtures.types import CommentModelAdapterT, ModelAdapterT
from form.base_form_tester import (
    AuthorisedSubmitTester,
    FormValidationException,
    SubmitTester,
)
from form.post.create_form_tester import CreatePostFormTester
from form.post.delete_tester import DeletePostTester
from form.post.edit_form_tester import EditPostFormTester
from form.post.find_urls import find_edit_and_delete_urls
from form.post.form_tester import PostFormTester
from test_content import MainPostContentTester, main_content_tester
from test_edit import _test_edit


@pytest.mark.parametrize(
    ("field", "type", "params", "field_error", "type_error", "param_error", "value_error"),
    [
        ("image", ImageField, {}, None, None, None, None),
        (
            "pub_date",
            DateTimeField,
            {"auto_now_add": False},
            None,
            None,
            None,
            (
                "Проверьте, что в модели Post в атрибуте pub_date параметр "
                "`auto_now_add` не установлен или имеет значение `False`. "
                "В ином случае станет невозможно публиковать посты "
                "задним числом и отложенные посты."
            ),
        ),
    ],
    ids=["`image` field", "`pub_date` field"],
)
class TestPostModelAttrs(_TestModelAttrs):
    @pytest.fixture(autouse=True)
    def _set_model(self):
        self._model = PostModelAdapter(Post)

    @property
    def model(self):
        return self._model


@pytest.mark.django_db(transaction=True)
def test_post_created_at(post_with_published_location):
    now = timezone.now()
    now_utc = now.astimezone(pytz.UTC).replace(tzinfo=None)
    assert abs(
        post_with_published_location.created_at.replace(tzinfo=None) - now_utc
    ) < datetime.timedelta(seconds=1), (
        "Убедитесь, что при создании поста ему присваиваются текущие дата и время."
    )


def _assert_404(client, url, err_msg):
    """Вспомогательная функция для проверки статуса 404 без дублирования try/except."""
    try:
        response = client.get(url)
        assert response.status_code == HTTPStatus.NOT_FOUND, err_msg
    except Post.DoesNotExist:
        raise AssertionError(err_msg)


@pytest.mark.django_db(transaction=True)
def test_post(
    published_category: Model,
    published_location: Model,
    user_client: django.test.Client,
    another_user_client: django.test.Client,
    unlogged_client: django.test.Client,
    comment_to_a_post: Model,
    create_post_context_form_item: Tuple[str, BaseForm],
    PostModel: Type[Model],
    CommentModelAdapter: CommentModelAdapterT,
    main_content_tester: MainPostContentTester,
):
    _, ctx_form = create_post_context_form_item

    create_a_post_get_response = get_create_a_post_get_response_safely(user_client)

    response_on_created, created_items = _test_create_items(
        PostModel,
        PostModelAdapter,
        another_user_client,
        create_a_post_get_response,
        ctx_form,
        published_category,
        published_location,
        unlogged_client,
        user_client,
    )

    # Проверка отображения картинок
    created_content = response_on_created.content.decode("utf-8")
    img_count = created_content.count("<img")
    expected_img_count = main_content_tester.n_or_page_size(len(created_items))
    assert img_count >= expected_img_count, (
        "Убедитесь, что при создании публикации она отображается с картинкой."
    )

    edit_response, edit_url, del_url = _test_edit_post(
        CommentModelAdapter,
        another_user_client,
        comment_to_a_post,
        unlogged_client=unlogged_client,
        user_client=user_client,
    )

    item_to_delete_adapter = PostModelAdapter(CommentModelAdapter(comment_to_a_post).post)
    del_url_addr = del_url.key

    # Проверка 404 для удаления
    del_unexisting_status_404_err_msg = (
        "Убедитесь, что при обращении к странице удаления "
        "несуществующего поста возвращается статус 404."
    )
    delete_tester = DeletePostTester(
        item_to_delete_adapter.item_cls,
        user_client,
        another_user_client,
        unlogged_client,
        item_adapter=item_to_delete_adapter,
    )
    delete_tester.test_delete_item(
        qs=item_to_delete_adapter.item_cls.objects.all(),
        delete_url_addr=del_url_addr,
    )
    try:
        AuthorisedSubmitTester(
            tester=delete_tester,
            test_response_cbk=SubmitTester.get_test_response_404_cbk(
                err_msg=delete_tester.nonexistent_obj_error_message
            ),
        ).test_submit(url=del_url_addr, data={})
    except Post.DoesNotExist:
        raise AssertionError(del_unexisting_status_404_err_msg)

    # Проверка 404 для просмотра и редактирования (объединено)
    _assert_404(
        user_client,
        f"/posts/{item_to_delete_adapter.id}/",
        "Убедитесь, что при обращении к странице несуществующего поста возвращается статус 404.",
    )
    _assert_404(
        user_client,
        edit_url[0],
        "Убедитесь, что при обращении к странице редактирования несуществующего поста возвращается статус 404.",
    )

    # === Контекстные менеджеры для изменения состояния поста ===
    @contextmanager
    def set_post_unpublished(post_adapter):
        is_published = post_adapter.is_published
        try:
            post_adapter.is_published = False
            post_adapter.save()
            yield
        finally:
            post_adapter.is_published = is_published
            post_adapter.save()

    @contextmanager
    def set_post_category_unpublished(post_adapter):
        category = post_adapter.category
        is_published = category.is_published
        try:
            category.is_published = False
            category.save()
            yield
        finally:
            category.is_published = is_published
            category.save()

    @contextmanager
    def set_post_postponed(post_adapter):
        pub_date = post_adapter.pub_date
        current_date = timezone.now()
        try:
            post_adapter.pub_date = post_adapter.pub_date.replace(
                year=current_date.year + 1, day=current_date.day - 1 or current_date.day
            )
            post_adapter.save()
            yield
        finally:
            post_adapter.pub_date = pub_date
            post_adapter.save()

    def check_post_access(client, post_adapter, err_msg, expected_status):
        url = f"/posts/{post_adapter.id}/"
        get_get_response_safely(client, url=url, err_msg=err_msg, expected_status=expected_status)

    # === Параметризация проверок доступа (убрано дублирование) ===
    detail_post_adapter = PostModelAdapter(created_items[0])
    access_scenarios = [
        (
            set_post_unpublished,
            "Убедитесь, что страница поста, снятого с публикации, доступна автору этого поста.",
            "Убедитесь, что страница поста, снятого с публикации, доступна только автору этого поста.",
        ),
        (
            set_post_category_unpublished,
            "Убедитесь, что страница поста, принадлежащего категории, снятой с публикации, доступна автору этого поста.",
            "Убедитесь, что страница поста, принадлежащего категории, снятой с публикации, доступна только автору этого поста.",
        ),
        (
            set_post_postponed,
            "Убедитесь, что страница отложенного поста доступна автору.",
            "Убедитесь, что страница отложенного поста доступна только автору.",
        ),
    ]

    for ctx_mgr, author_msg, other_msg in access_scenarios:
        with ctx_mgr(detail_post_adapter):
            check_post_access(user_client, detail_post_adapter, author_msg, HTTPStatus.OK)
            check_post_access(another_user_client, detail_post_adapter, other_msg, HTTPStatus.NOT_FOUND)


def _test_create_items(
    PostModel,
    PostAdapter,
    another_user_client,
    create_a_post_get_response,
    ctx_form,
    published_category,
    published_location,
    unlogged_client,
    user_client,
) -> Tuple[HttpResponse, List[ModelAdapterT]]:
    creation_tester = CreatePostFormTester(
        create_a_post_get_response,
        PostModel,
        user_client,
        another_user_client,
        unlogged_client,
        ModelAdapter=PostAdapter,
        item_adapter=None,
    )
    Form: Type[BaseForm] = type(ctx_form)
    item_ix_start: int = random.randint(1_000_000, 2_000_000)
    forms_data = [
        {
            "title": f"Test create post {i} title",
            "text": f"Test create post {i} text",
            "pub_date": timezone.now(),
            "category": published_category,
            "location": published_location,
        }
        for i in range(item_ix_start, item_ix_start + 5)
    ]

    forms_to_create = creation_tester.init_create_item_forms(
        Form, Model=PostModel, ModelAdapter=PostAdapter, forms_unadapted_data=forms_data
    )

    try:
        creation_tester.test_unlogged_cannot_create(form=forms_to_create[0], qs=PostModel.objects.all())
    except FormValidationException as e:
        raise AssertionError(
            f"Убедитесь, что для валидации {creation_tester.of_which_form} достаточно заполнить "
            f"следующие поля: {list(forms_to_create[0].data.keys())}. При валидации формы возникли ошибки: {e}"
        )

    response_on_created, created_items = creation_tester.test_create_several(
        forms=forms_to_create[1:], qs=PostModel.objects.all()
    )
    content = response_on_created.content.decode(encoding="utf8")

    # Оптимизированная проверка редиректа
    author_username = PostAdapter(created_items[0]).author.username
    redirected_to_profile = any(
        f"/profile/{author_username}" in redirect_url for redirect_url, _ in response_on_created.redirect_chain
    )
    assert response_on_created.redirect_chain and redirected_to_profile, (
        "Убедитесь, что при создании поста пользователь перенаправляется на страницу своего профиля "
        "по адресу `profile/<username>/`."
    )

    creation_tester.test_creation_response(content, created_items)
    return response_on_created, created_items


def _test_edit_post(
    CommentModelAdapter,
    another_user_client,
    comment_to_a_post,
    unlogged_client,
    user_client,
) -> Tuple[HttpResponse, KeyVal, KeyVal]:
    comment_adapter = CommentModelAdapter(comment_to_a_post)
    item_to_edit = comment_adapter.post
    post_adapter = PostModelAdapter(item_to_edit)
    post_url = f"/posts/{item_to_edit.id}/"
    response_on_commented = user_client.get(post_url)

    edit_url, del_url = find_edit_and_delete_urls(
        post_adapter,
        comment_adapter,
        response_on_commented,
        urls_start_with=KeyVal(
            key=post_url.replace(f"/{item_to_edit.id}/", "/<post_id>/"),
            val=post_url,
        ),
    )
    assert edit_url.key == f"/posts/{item_to_edit.id}/edit/", (
        "Убедитесь, что адрес страницы редактирования поста - `posts/<post_id>/edit/`."
    )
    edit_url = KeyVal(re.sub(r"\d+", str(item_to_edit.id), edit_url.key), edit_url.val)

    item_to_edit_adapter = PostModelAdapter(item_to_edit)
    update_props = {
        item_to_edit_adapter.item_cls_adapter.displayed_field_name_or_value: (
            f"{item_to_edit_adapter.displayed_field_name_or_value} edited"
        )
    }

    return _test_edit(
        edit_url,
        PostModelAdapter,
        item_to_edit,
        EditFormTester=EditPostFormTester,
        user_client=user_client,
        another_user_client=another_user_client,
        unlogged_client=unlogged_client,
        file_data=PostFormTester.generate_files_dict(),
        **update_props,
    )