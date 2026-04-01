
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from blog.models import Post, Category, Comments
from .forms import UserForm, PostForm, CommentForm
from blog.additional_functions import get_posts, pagination

User = get_user_model()


def index(request):
    template_name = 'blog/index.html'
    post_list = get_posts(True, True)
    print("!!!!!!!!!!!!!", post_list)
    page_obj = pagination(post_list, request)
    context = {'page_obj': page_obj}
    return render(request, template_name, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(get_posts(True), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


def post_detail(request, post_id):
    template_name = 'blog/detail.html'
    post = get_object_or_404(get_posts(False, True),
                             pk=post_id)

    if post.author != request.user:
        post = get_object_or_404(get_posts(True, True),
                                 pk=post_id)

    comments = post.comments.all()
    form = CommentForm()
    context = {'post': post, 'form': form, 'comments': comments}
    return render(request, template_name, context)


@login_required
def edit_comment(request, post_id=None, comment_id=None):
    template_name = 'blog/comment.html'
    post = get_object_or_404(get_posts(True), pk=post_id)

    comment = get_object_or_404(
        Comments.objects.select_related('author'), id=comment_id,
        author__username=request.user, post__id=post_id
    )

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post_id)
    context = {'form': form, 'comment': comment}
    return render(request, template_name, context)


@login_required
def delete_comment(request, post_id=None, comment_id=None):
    template_name = 'blog/comment.html'

    comment = get_object_or_404(
        Comments.objects.select_related('author'),
        id=comment_id, post__id=post_id, author__username=request.user)

    if request.method == "POST":
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    context = {'comment': comment}
    return render(request, template_name, context)


def category_posts(request, category_slug):
    template_name = 'blog/category.html'
    category = get_object_or_404(Category, slug=category_slug,
                                 is_published=True)
    post_list = get_posts(True, False, category.posts)
    page_obj = pagination(post_list, request)
    context = {'category': category, 'page_obj': page_obj}
    return render(request, template_name, context)


def profile(request, username):
    template_name = 'blog/profile.html'
    profile = get_object_or_404(get_user_model(), username=username)
    post_list = get_posts(profile != request.user, True, profile.posts)
    page_obj = pagination(post_list, request)
    context = {'profile': profile, 'page_obj': page_obj}
    return render(request, template_name, context)


@login_required
def create_post(request, pk=None):
    template_name = 'blog/create.html'
    form = PostForm(request.POST or None, files=request.FILES or None)
    context = {'form': form}
    if form.is_valid():
        new_Post = form.save(commit=False)
        new_Post.author = request.user
        new_Post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template_name, context)


@login_required
def edit_post(request, post_id):
    template_name = 'blog/create.html'
    instance = get_object_or_404(Post, pk=post_id)
    if instance.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=instance)
    context = {'form': form}
    if form.is_valid():
        new_Post = form.save(commit=False)
        new_Post.author = request.user
        new_Post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template_name, context)


@login_required
def delete_post(request, post_id):
    template_name = 'blog/create.html'
    instance = get_object_or_404(Post, pk=post_id, author=request.user)
    form = PostForm(instance=instance)
    context = {'form': form}
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template_name, context)


@login_required
def edit_profile(request):
    template_name = 'blog/user.html'
    instance = request.user
    form = UserForm(request.POST or None, instance=instance)
    context = {'form': form}
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template_name, context)
