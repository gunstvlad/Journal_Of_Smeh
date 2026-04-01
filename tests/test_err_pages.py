import importlib
import inspect
import uuid
from pathlib import Path

import pytest
from django.conf import settings
from django.http import HttpRequest
from pytest_django.asserts import assertTemplateUsed


def _get_callable_from_path(dotted_path: str):
    """Вспомогательная функция: импортирует объект по строке вида 'module.func'."""
    try:
        module_name, func_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)
    except (ImportError, AttributeError, ValueError):
        return None


def test_csrf_failure_view():
    csrf_failure_view_path = getattr(settings, "CSRF_FAILURE_VIEW", "")
    csrf_failure_view = _get_callable_from_path(csrf_failure_view_path)

    assert csrf_failure_view is not None, (
        "Убедитесь, что в `settings.py` задана настройка `CSRF_FAILURE_VIEW` и "
        "что она указывает на существующую view-функцию."
    )

    request = HttpRequest()
    request.method = "POST"
    request.POST = {}

    try:
        response = csrf_failure_view(request)
    except Exception as exc:
        raise AssertionError(
            f"Убедитесь, что view-функция `{csrf_failure_view_path}` работает без ошибок."
        ) from exc

    assert response.status_code == 403, (
        f"Убедитесь, что view-функция `{csrf_failure_view_path}` возвращает статус 403."
    )


@pytest.mark.django_db
def test_custom_err_handlers(client, user_client):
    err_pages = {
        404: "404.html",
        403: "403csrf.html",
        500: "500.html",
    }

    # Безопасное получение пути к шаблонам (работает и со str, и с pathlib.Path)
    templates_dir = getattr(settings, "TEMPLATES_DIR", None)
    assert templates_dir is not None, (
        "Убедитесь, что переменная TEMPLATES_DIR задана в настройках проекта."
    )
    pages_dir = Path(templates_dir) / "pages"

    # Проверка существования файлов шаблонов
    for _, fname in err_pages.items():
        fpath = pages_dir / fname
        assert fpath.is_file(), (
            f"Убедитесь, что файл шаблона `{fpath}` существует."
        )

    # Проверка handler500
    try:
        from blogicum.blog.urls import handler500
        handler500_path = handler500
    except Exception:
        raise AssertionError(
            "Убедитесь, что в головном файле с маршрутами нет ошибок и что в "
            "нём задан обработчик ошибки 500."
        )

    assert _get_callable_from_path(handler500_path) is not None, (
        "Убедитесь, что обработчик ошибки 500 в головном файле с маршрутами "
        "указывает на существующую функцию."
    )

    # Проверка исходного кода pages/views.py
    try:
        from blogicum.pages import views as pages_views
    except Exception:
        raise AssertionError("Убедитесь, что в файле `pages/views.py` нет ошибок.")

    source_code = inspect.getsource(pages_views)
    for status, fname in err_pages.items():
        # 🔍 ИСПРАВЛЕНИЕ: в оригинале отсутствовал префикс f, из-за чего {status} и {fname} 
        # выводились как текст. Добавлен f для корректной интерполяции.
        assert fname in source_code, (
            f"Проверьте view-функции приложения `pages`: убедитесь, что для "
            f"генерации страниц со статусом ответа `{status}` используется "
            f"шаблон `pages/{fname}`"
        )

    # Проверка рендеринга 404 шаблона
    original_debug = settings.DEBUG
    settings.DEBUG = False
    try:
        # uuid.uuid4() возвращает объект, приводим к str для безопасности client.get()
        non_existing_url = str(uuid.uuid4())
        response = client.get(non_existing_url)
        assertTemplateUsed(
            response,
            "pages/404.html",
            "Убедитесь, что для страниц со статусом ответа `404` используется шаблон `pages/404.html`",
        )
    finally:
        settings.DEBUG = original_debug