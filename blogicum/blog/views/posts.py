from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from ..models import Post, Category
from ..forms import PostForm
from ..additional_functions import get_posts, pagination


def index(request):
    """Главная страница блога"""
    template_name = 'blog/index.html'
    post_list = get_posts(True, True)
    page_obj = pagination(post_list, request)
    context = {'page_obj': page_obj}
    return render(request, template_name, context)


def post_detail(request, post_id):
    """Детальная страница поста"""
    template_name = 'blog/detail.html'
    post = get_object_or_404(get_posts(False, True), pk=post_id)

    # Если пользователь не автор, показываем только опубликованные
    if post.author != request.user:
        post = get_object_or_404(get_posts(True, True), pk=post_id)

    comments = post.comments.all()
    # Форму комментария создаём здесь, так как она используется в шаблоне поста
    from blog.forms import CommentForm
    form = CommentForm()
    
    context = {'post': post, 'form': form, 'comments': comments}
    return render(request, template_name, context)


def category_posts(request, category_slug):
    """Посты конкретной категории"""
    template_name = 'blog/category.html'
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    post_list = get_posts(True, False, category.posts)
    page_obj = pagination(post_list, request)
    context = {'category': category, 'page_obj': page_obj}
    return render(request, template_name, context)


@login_required
def create_post(request, pk=None):
    """Создание нового поста"""
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
    """Редактирование поста"""
    template_name = 'blog/create.html'
    instance = get_object_or_404(Post, pk=post_id)
    if instance.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    
    form = PostForm(request.POST or None, files=request.FILES or None, instance=instance)
    context = {'form': form}
    if form.is_valid():
        new_Post = form.save(commit=False)
        new_Post.author = request.user
        new_Post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template_name, context)


@login_required
def delete_post(request, post_id):
    """Удаление поста"""
    template_name = 'blog/create.html'
    instance = get_object_or_404(Post, pk=post_id, author=request.user)
    form = PostForm(instance=instance)
    context = {'form': form}
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, template_name, context)