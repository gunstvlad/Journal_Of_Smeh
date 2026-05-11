# blog/views/__init__.py
from .posts import (
    index,
    post_detail,
    category_posts,
    create_post,
    edit_post,
    delete_post,
)
from .comments import add_comment, edit_comment, delete_comment
from .profile import profile, edit_profile
from .meme import generate_meme, meme_gallery, save_meme_as_post

__all__ = [
    "index",
    "post_detail",
    "category_posts",
    "create_post",
    "edit_post",
    "delete_post",
    "add_comment",
    "edit_comment",
    "delete_comment",
    "profile",
    "edit_profile",
    "generate_meme",
    "meme_gallery",
    "save_meme_as_post",
]
