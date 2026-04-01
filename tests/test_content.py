import inspect
from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple, Type, Union

import pytest
from bs4 import BeautifulSoup, SoupStrainer
from django.db.models import Model
from django.http import HttpResponse
from django.test.client import Client
from mixer.main import Mixer

from adapters.model_adapter import ModelAdapter
from adapters.post import PostModelAdapter
from conftest import (
    N_PER_PAGE,
    UrlRepr,
    _testget_context_item_by_class,
    _testget_context_item_by_key,
)

pytestmark = [pytest.mark.django_db]


class ContentTester(ABC):
    n_per_page = N_PER_PAGE

    def __init__(
        self,
        mixer: Mixer,
        item_cls: Type[Model],
        adapter_cls: Type[ModelAdapter],
        user_client: Client,
        page_url: Optional[UrlRepr] = None,
        another_user_client: Optional[Client] = None,
        unlogged_client: Optional[Client] = None,
    ):
        self._mixer = mixer
        self._items_key = None
        self._page_url = page_url
        self.item_cls = item_cls
        self.adapter_cls = adapter_cls
        self.user_client = user_client
        self.another_user_client = another_user_client
        self.unlogged_client = unlogged_client

    @property
    def page_url(self):
        return self._page_url

    @property
    @abstractmethod
    def items_hardcoded_key(self):
        raise NotImplementedError

    @abstractmethod
    def raise_assert_page_loads_cbk(self):
        raise NotImplementedError

    def user_client_testget(
        self,
        url: Optional[str] = None,
        assert_status_in: Tuple[int, ...] = (200,),
        assert_cbk: Union[Callable[[], None], str] = "raise_assert_page_loads_cbk",
    ) -> HttpResponse:
        return self._testget(self.user_client, url, assert_status_in, assert_cbk)

    def another_client_testget(
        self,
        url: Optional[str] = None,
        assert_status_in: Tuple[int, ...] = (200,),
        assert_cbk: Union[Callable[[], None], str] = "raise_assert_page_loads_cbk",
    ) -> HttpResponse:
        return self._testget(self.another_user_client, url, assert_status_in, assert_cbk)

    def _testget(
        self,
        client: Client,
        url: Optional[str],
        assert_status_in: Tuple[int, ...],
        assert_cbk: Union[Callable[[], None], str],
    ) -> HttpResponse:
        url = url or self.page_url.url
        try:
            response = client.get(url)
            if response.status_code not in assert_status_in:
                raise Exception
        except Exception:
            if inspect.isfunction(assert_cbk):
                assert_cbk()
            elif isinstance(assert_cbk, str):
                getattr(self, assert_cbk)()
            else:
                raise AssertionError("Wrong type of `assert_cbk` argument.")
        return response

    @abstractmethod
    def items_key_error_message(self):
        raise NotImplementedError

    @abstractmethod
    def items_hardcoded_key_error_message(self):
        raise NotImplementedError

    def safe_get_items_key(self):
        try:
            return self.items_key
        except AssertionError:
            return None

    @property
    def items_key(self):
        if self._items_key:
            return self._items_key

        setup_items: List[Model] = []

        def setup_for_url() -> UrlRepr:
            temp_category = self._mixer.blend("blog.Category", is_published=True)
            temp_location = self._mixer.blend("blog.Location", is_published=True)
            temp_post = self._mixer.blend(
                "blog.Post", is_published=True, location=temp_location, category=temp_category
            )
            setup_items.extend([temp_category, temp_location, temp_post])
            return self.page_url

        def teardown():
            for item in reversed(setup_items):
                item.delete()

        try:
            url_repr = setup_for_url()
            context = self.user_client_testget(url=url_repr.url).context

            if self.items_hardcoded_key:
                key_val = _testget_context_item_by_key(
                    context, self.items_hardcoded_key, err_msg=self.items_hardcoded_key_error_message()
                )
            else:
                key_val = _testget_context_item_by_class(
                    context, self.item_cls, err_msg=self.items_key_error_message(), inside_iter=True
                )
            self._items_key = key_val.key
        finally:
            teardown()

        return self._items_key

    def n_or_page_size(self, n: int):
        return min(self.n_per_page, n)


class PostContentTester(ContentTester):
    @property
    def items_hardcoded_key(self):
        return "page_obj"

    @abstractmethod
    def raise_assert_page_loads_cbk(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def image_display_error(self) -> str:
        raise NotImplementedError


class ProfilePostContentTester(PostContentTester):
    def items_key_error_message(self):
        return "Убедитесь, что существует ровно один ключ, под которым в словарь контекста страницы пользователя передаются публикации."

    def items_hardcoded_key_error_message(self):
        return f"Убедитесь, что в словарь контекста страницы пользователя публикации передаются под ключом `{self.items_hardcoded_key}`."

    def raise_assert_page_loads_cbk(self):
        raise AssertionError("Убедитесь, что страница пользователя загружается без ошибок.")

    @property
    def image_display_error(self) -> str:
        return "Убедитесь, что на странице профиля автора отображаются изображения публикаций."


class MainPostContentTester(PostContentTester):
    def items_key_error_message(self):
        return "Убедитесь, что существует ровно один ключ, под которым в словарь контекста главной страницы передаются публикации."

    def items_hardcoded_key_error_message(self):
        return f"Убедитесь, что в словарь контекста главной страницы публикации передаются под ключом `{self.items_hardcoded_key}`."

    def raise_assert_page_loads_cbk(self):
        raise AssertionError("Убедитесь, что главная страница загружается без ошибок.")

    @property
    def image_display_error(self) -> str:
        return "Убедитесь, что на главной странице видны прикреплённые к постам изображения."


class CategoryPostContentTester(PostContentTester):
    @property
    def page_url(self):
        if not self._page_url:
            from blogicum.blog.models import Category

            category = Category.objects.first()
            if category:
                self._page_url = UrlRepr(f"/category/{category.slug}/", "/category/<category_slug>/")
        return self._page_url

    def items_key_error_message(self):
        return "Убедитесь, что существует ровно один ключ, под которым в словарь контекста страницы категории передаются публикации."

    def items_hardcoded_key_error_message(self):
        return f"Убедитесь, что в словарь контекста страницы категории публикации передаются под ключом `{self.items_hardcoded_key}`."

    def raise_assert_page_loads_cbk(self):
        raise AssertionError("Убедитесь, что страница категории загружается без ошибок.")

    @property
    def image_display_error(self) -> str:
        return "Убедитесь, что на странице категории видны прикреплённые к постам изображения."


@pytest.fixture
def profile_content_tester(
    user: Model, mixer: Mixer, PostModel: Type[Model], user_client: Client, another_user_client: Client
) -> ProfilePostContentTester:
    url_repr = UrlRepr(f"/profile/{user.username}/", "/profile/<username>/")
    return ProfilePostContentTester(mixer, PostModel, PostModelAdapter, user_client, url_repr, another_user_client)


@pytest.fixture
def main_content_tester(
    mixer: Mixer, PostModel: Type[Model], user_client: Client
) -> MainPostContentTester:
    return MainPostContentTester(mixer, PostModel, PostModelAdapter, user_client, UrlRepr("/", "/"))


@pytest.fixture
def category_content_tester(
    mixer: Mixer, PostModel: Type[Model], user_client: Client
) -> CategoryPostContentTester:
    return CategoryPostContentTester(mixer, PostModel, PostModelAdapter, user_client)


class TestContent:
    @pytest.fixture(autouse=True)
    def init(
        self, profile_content_tester, main_content_tester, category_content_tester
    ):
        self.profile_tester = profile_content_tester
        self.main_tester = main_content_tester
        self.category_tester = category_content_tester

    def _check_post_count(self, tester, expected_count, err_msg):
        response = tester.user_client_testget()
        items_key = tester.safe_get_items_key()
        if items_key is None:
            return
        context_posts = response.context.get(items_key)
        assert len(context_posts) == expected_count, err_msg

    def test_unpublished(self, unpublished_posts_with_published_locations):
        expected_n = self.profile_tester.n_or_page_size(len(unpublished_posts_with_published_locations))
        self._check_post_count(
            self.profile_tester, expected_n,
            "Убедитесь, что на странице пользователя автор может видеть свои посты, снятые с публикации."
        )
        self._check_post_count(
            self.main_tester, 0,
            "Убедитесь, что на главной странице не отображаются посты, снятые с публикации."
        )
        self._check_post_count(
            self.category_tester, 0,
            "Убедитесь, что на странице категории не отображаются посты, снятые с публикации."
        )

    def test_only_own_pubs_in_category(self, post_with_published_location, post_with_another_category):
        self._check_post_count(
            self.category_tester, 1,
            "Убедитесь, что на странице категории не отображаются публикации других категорий."
        )

    def test_only_own_pubs_in_profile(self, post_with_published_location, post_of_another_author):
        self._check_post_count(
            self.profile_tester, 1,
            "Убедитесь, что на странице пользователя не отображаются публикации других авторов."
        )

    def test_unpublished_category(self, posts_with_unpublished_category):
        expected_n = self.profile_tester.n_or_page_size(len(posts_with_unpublished_category))
        self._check_post_count(
            self.profile_tester, expected_n,
            "Убедитесь, что на странице пользователя автор может видеть свои посты, принадлежащие категории, снятой с публикации."
        )
        self._check_post_count(
            self.main_tester, 0,
            "Убедитесь, что на главной странице не отображаются посты, принадлежащие категории, снятой с публикации."
        )
        def raise_assert_not_exist_cbk():
            raise AssertionError("Убедитесь, что страница категории недоступна, если категория снята с публикации.")
        self.category_tester.user_client_testget(
            assert_status_in=(404,), assert_cbk=raise_assert_not_exist_cbk
        )

    def test_future_posts(self, future_posts):
        expected_n = self.profile_tester.n_or_page_size(len(future_posts))
        self._check_post_count(
            self.profile_tester, expected_n,
            "Убедитесь, что на странице пользователя автор может видеть свои отложенные публикации."
        )
        self._check_post_count(
            self.main_tester, 0,
            "Убедитесь, что на главной странице не отображаются отложенные публикации."
        )
        self._check_post_count(
            self.category_tester, 0,
            "Убедитесь, что на странице категории не отображаются отложенные публикации."
        )

    def test_pagination(self, many_posts_with_published_locations):
        posts = many_posts_with_published_locations
        assert len(posts) > self.profile_tester.n_per_page

        test_cases = [
            {
                "tester": self.profile_tester,
                "func": self.profile_tester.user_client_testget,
                "ordering_err": "Убедитесь, что публикации передаются в контекст страницы профиля автора отсортированными по времени их публикации, «от новых к старым».",
                "pagination_err": "Убедитесь, что на странице профиля автора работает пагинация.",
            },
            {
                "tester": self.profile_tester,
                "func": self.profile_tester.another_client_testget,
                "ordering_err": "Убедитесь, что публикации передаются в контекст страницы профиля автора отсортированными по времени их публикации, «от новых к старым».",
                "pagination_err": "Убедитесь, что на странице профиля автора пагинация работает в соответствии с заданием.",
            },
            {
                "tester": self.main_tester,
                "func": self.main_tester.user_client_testget,
                "ordering_err": "Убедитесь, что публикации передаются в контекст главной страницы отсортированными по времени их публикации, «от новых к старым».",
                "pagination_err": "Убедитесь, что на главной странице пагинация работает в соответствии с заданием.",
            },
            {
                "tester": self.category_tester,
                "func": self.category_tester.user_client_testget,
                "ordering_err": "Убедитесь, что публикации передаются в контекст страницы категории отсортированными по времени их публикации, «от новых к старым».",
                "pagination_err": "Убедитесь, что на странице категории пагинация работает в соответствии с заданием.",
            },
        ]

        for case in test_cases:
            tester = case["tester"]
            response = case["func"]()
            context_posts = response.context.get(tester.items_key)
            pub_dates = [x.pub_date for x in context_posts]
            if pub_dates != sorted(pub_dates, reverse=True):
                raise AssertionError(case["ordering_err"])
            expected_n = tester.n_or_page_size(len(posts))
            assert len(context_posts) == expected_n, case["pagination_err"]

    def test_image_visible(self, user_client, post_with_published_location):
        post = post_with_published_location
        post_adapter = PostModelAdapter(post)
        testers: List[PostContentTester] = [self.profile_tester, self.main_tester, self.category_tester]
        img_counts_with_img = {}

        for i, tester in enumerate(testers):
            soup = BeautifulSoup(
                tester.user_client_testget().content.decode("utf-8"),
                features="html.parser",
                parse_only=SoupStrainer("img"),
            )
            img_counts_with_img[i] = len(soup)

        post_adapter.image = None
        post_adapter.save()

        for i, tester in enumerate(testers):
            soup = BeautifulSoup(
                tester.user_client_testget().content.decode("utf-8"),
                features="html.parser",
                parse_only=SoupStrainer("img"),
            )
            count_without = len(soup)
            assert (img_counts_with_img[i] - count_without) == 1, tester.image_display_error