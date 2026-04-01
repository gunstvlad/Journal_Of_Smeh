import inspect
import os
from http import HTTPStatus
from pathlib import Path
from typing import List, Optional, Set, Tuple

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.http import HttpResponse
from django.urls import URLPattern, URLResolver, get_resolver

from adapters.user import UserModelAdapter
from conftest import KeyVal, squash_code
from form.find_urls import find_links_between_lines
from form.user.edit_form_tester import EditUserFormTester
from test_edit import _test_edit


class ManageProfileLinksException(Exception): ...


def _search_url_patterns(substring: str) -> List:
    """Рекурсивный поиск URL-паттернов, содержащих заданную подстроку."""
    resolver = get_resolver()
    results = []

    def _recursive_search(head: str, patterns):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):
                full_pattern = head + str(pattern.pattern)
                if substring in full_pattern:
                    results.append(pattern)
            elif isinstance(pattern, URLResolver):
                _recursive_search(head + str(pattern.pattern), pattern.url_patterns)

    _recursive_search("", resolver.url_patterns)
    return results


@pytest.mark.django_db
def test_custom_err_handlers(client):
    try:
        from blogicum import urls as blogicum_urls
    except Exception:
        raise AssertionError("Убедитесь, в головном файле с маршрутами нет ошибок.")

    urls_src_squashed = squash_code(inspect.getsource(blogicum_urls))
    if "django.contrib.auth.urls" not in urls_src_squashed:
        raise AssertionError(
            "Убедитесь, что подключены маршруты для работы с пользователями из"
            " `django.contrib.auth.urls`."
        )

    registration_url = "auth/registration/"
    assert _search_url_patterns(registration_url), (
        "Убедитесь, что в головном файле с маршрутами переопределён маршрут"
        f" `{registration_url}`."
    )

    auth_templates = {
        "logged_out.html", "login.html", "password_change_done.html",
        "password_change_form.html", "password_reset_complete.html",
        "password_reset_confirm.html", "password_reset_done.html",
        "password_reset_form.html", "registration_form.html",
    }

    templates_dir = getattr(settings, "TEMPLATES_DIR", None)
    assert templates_dir is not None, (
        "Убедитесь, что переменная TEMPLATES_DIR задана в настройках проекта."
    )
    reg_dir = Path(templates_dir) / "registration"

    for template in auth_templates:
        try:
            fpath = reg_dir / template
        except Exception as e:
            raise AssertionError(
                "Убедитесь, что переменная TEMPLATES_DIR в настройках проекта "
                "является строкой (str) или объектом, соответствующим path-like интерфейсу "
                "(например, экземпляром pathlib.Path). "
                f'При операции Path(settings.TEMPLATES_DIR) / "registration", возникла ошибка: {e}'
            )
        
        assert fpath.is_file(), (
            f"Убедитесь, что файл шаблона `{fpath.relative_to(settings.BASE_DIR)}` существует."
        )


@pytest.mark.django_db
def test_profile(user, another_user, user_client, another_user_client, unlogged_client):
    user_url = f"/profile/{user.username}/"
    printed_url = "/profile/<username>/"

    User = get_user_model()
    status_code_not_404_err_msg = (
        "Убедитесь, что при обращении к странице несуществующего "
        "пользователя возвращается статус 404."
    )
    try:
        response = user_client.get("/profile/this_is_unexisting_user_name/")
    except User.DoesNotExist:
        raise AssertionError(status_code_not_404_err_msg)
    assert response.status_code == HTTPStatus.NOT_FOUND, status_code_not_404_err_msg

    clients = {"user": user_client, "another": another_user_client, "unlogged": unlogged_client}
    contents = {name: client.get(user_url).content.decode("utf-8") for name, client in clients.items()}

    for content_key in ("user", "unlogged", "another"):
        _test_user_info_displayed(user, contents[content_key], printed_url)
    try:
        edit_url, change_pwd_url = try_get_profile_manage_urls(
            contents["user"], contents["another"], ignore_urls={user_url}
        )
    except ManageProfileLinksException:
        raise AssertionError(
            "Убедитесь, что на странице профиля пользователя ссылки для"
            " редактирования профиля и изменения пароля видны только владельцу"
            " профиля, но не другим пользователям."
        )

    unlogged_diff_urls = get_extra_urls(
        base_content=contents["unlogged"], extra_content=contents["user"]
    )
    assert {edit_url, change_pwd_url}.issubset(set(unlogged_diff_urls)), (
        "Убедитесь, что неаутентифицированному пользователю недоступны ссылки"
        " для редактирования профиля и изменения пароля."
    )

    item_to_edit_adapter = UserModelAdapter(user)
    old_prop_value = item_to_edit_adapter.displayed_field_name_or_value
    update_props = {
        item_to_edit_adapter.item_cls_adapter.displayed_field_name_or_value: (
            f"{old_prop_value} edited"
        )
    }
    _test_edit(
        KeyVal(edit_url, edit_url),
        UserModelAdapter,
        user,
        EditFormTester=EditUserFormTester,
        user_client=user_client,
        unlogged_client=unlogged_client,
        **update_props,
    )


def _test_user_info_displayed(profile_user: Model, profile_user_content: str, printed_url: str) -> None:
    if profile_user.first_name not in profile_user_content:
        raise AssertionError(
            f"Убедитесь, что на странице `{printed_url}` отображается имя пользователя."
        )
    if profile_user.last_name not in profile_user_content:
        raise AssertionError(
            f"Убедитесь, что на странице `{printed_url}` отображается фамилия пользователя."
        )


def try_get_profile_manage_urls(
    user_content: str, anothers_page_content: str, ignore_urls: Set[str]
) -> Tuple[str, str]:
    diff_urls = get_extra_urls(
        base_content=anothers_page_content,
        extra_content=user_content,
        ignore_urls=ignore_urls,
    )
    if len(diff_urls) != 2:
        raise ManageProfileLinksException

    edit_url, change_pwd_url = diff_urls
    change_pwd_marker = "/auth/password_change/"
    if change_pwd_marker in edit_url:
        edit_url, change_pwd_url = change_pwd_url, edit_url

    if change_pwd_marker not in change_pwd_url:
        raise AssertionError(
            "Убедитесь, что на странице профиля владельцу этого профиля"
            f" доступна ссылка `{change_pwd_marker}` для изменения пароля."
        )
    return edit_url, change_pwd_url


def get_extra_urls(
    base_content: str,
    extra_content: str,
    ignore_urls: Optional[Set[str]] = None,
) -> List[str]:
    ignore_urls = ignore_urls or set()
    find_kwargs = {"urls_start_with": "", "start_lineix": -1, "end_lineix": -1}

    user_hrefs = {link.get("href") for link in find_links_between_lines(extra_content, **find_kwargs)}
    others_hrefs = {link.get("href") for link in find_links_between_lines(base_content, **find_kwargs)}

    return [url for url in (user_hrefs - others_hrefs) if url not in ignore_urls]