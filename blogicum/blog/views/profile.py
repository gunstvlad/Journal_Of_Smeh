from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from ..forms import UserForm
from ..additional_functions import get_posts, pagination

User = get_user_model()


@login_required
def edit_profile(request):
    """Редактирование профиля пользователя"""
    template_name = "blog/user.html"
    instance = request.user
    form = UserForm(request.POST or None, instance=instance)
    context = {"form": form}
    if form.is_valid():
        form.save()
        return redirect("blog:profile", username=request.user.username)
    return render(request, template_name, context)


def profile(request, username):
    """Публичная страница профиля пользователя"""
    template_name = "blog/profile.html"
    profile = get_object_or_404(User, username=username)
    # Если смотрит не владелец → показываем только опубликованные посты
    post_list = get_posts(profile != request.user, True, profile.posts)
    page_obj = pagination(post_list, request)
    context = {"profile": profile, "page_obj": page_obj}
    return render(request, template_name, context)
