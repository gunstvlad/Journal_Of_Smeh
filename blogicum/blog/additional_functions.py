from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q

from blog.models import Post
from django.conf import settings


def get_posts(apply_filters=False, comment_count=False, manager=Post.objects, for_user=None):
    queryset = manager.select_related("category", "author", "location")
    
    if comment_count:
        queryset = queryset.annotate(comment_count=Count("comments"))
    
    if apply_filters:
        if for_user:
            queryset = queryset.filter(
                Q(is_published=True, category__is_published=True, pub_date__lt=timezone.now() + timezone.timedelta(hours=3)) |
                Q(author=for_user)
            )
        else:
            queryset = queryset.filter(
                is_published=True,
                category__is_published=True,
                pub_date__lt=timezone.now() + timezone.timedelta(hours=3),
            )
            
    return queryset.order_by("-pub_date")


def pagination(post_list, request):
    return Paginator(post_list, settings.PAGINATION_AMOUNT).get_page(
        request.GET.get("page")
    )
