
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count

from blog.models import Post
from django.conf import settings


def get_posts(apply_filters=False, comment_count=False,
              menedger=Post.objects):
    queryset = menedger.select_related('category',
                                       'author',
                                       'location')
    if comment_count:
        queryset = queryset.annotate(
            comment_count=Count(
                'comments'
            )
        )
    print("!!!!!!!!!!!!!", timezone.now())
    if apply_filters:
        queryset = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lt=timezone.now()+timezone.timedelta(hours=3)
        )
    return queryset.order_by('-pub_date',)


def pagination(post_list, request):
    return Paginator(
        post_list, settings.PAGINATION_AMOUNT
    ).get_page(request.GET.get('page'))
