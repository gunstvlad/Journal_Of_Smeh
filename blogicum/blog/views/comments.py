from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from ..models import Post, Comments
from ..forms import CommentForm
from ..additional_functions import get_posts


@login_required
def add_comment(request, post_id):
    """Добавление комментария к посту"""
    post = get_object_or_404(get_posts(True), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect("blog:post_detail", post_id=post_id)


@login_required
def edit_comment(request, post_id=None, comment_id=None):
    """Редактирование комментария"""
    template_name = "blog/comment.html"
    post = get_object_or_404(get_posts(True), pk=post_id)

    comment = get_object_or_404(
        Comments.objects.select_related("author"),
        id=comment_id,
        author__username=request.user,
        post__id=post_id,
    )

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect("blog:post_detail", post_id=post_id)

    context = {"form": form, "comment": comment}
    return render(request, template_name, context)


@login_required
def delete_comment(request, post_id=None, comment_id=None):
    """Удаление комментария"""
    template_name = "blog/comment.html"

    comment = get_object_or_404(
        Comments.objects.select_related("author"),
        id=comment_id,
        post__id=post_id,
        author__username=request.user,
    )

    if request.method == "POST":
        comment.delete()
        return redirect("blog:post_detail", post_id=post_id)

    context = {"comment": comment}
    return render(request, template_name, context)
