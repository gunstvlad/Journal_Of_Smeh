from django import forms
from django.contrib.auth import get_user_model

from blog.models import Post, Comments

User = get_user_model()


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = ['title', 'text', 'location', 'category', 'pub_date', 'image']
        widgets = {
            'pub_date': forms.DateTimeInput(attrs={'type': 'datetime-local'},
                                            format='%Y-%m-%dT%H:%M')
        }


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comments
        fields = ('text',)
