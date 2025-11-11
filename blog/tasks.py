from celery import shared_task
from django.db.models import Count, F
from .models import Post, Reaction, Comment


@shared_task
def increment_post_view_count(post_id):
    """
    Increments the view count of a post.
    """
    try:
        post = Post.objects.get(id=post_id)
        post.views_count = F("views_count") + 1
        post.save(update_fields=["views_count"])
    except Post.DoesNotExist:
        # Handle the case where the post might have been deleted
        pass


@shared_task
def update_post_counts(post_id):
    """
    Recalculates and updates the comments and likes count for a post.
    """
    try:
        post = Post.objects.get(id=post_id)

        # Update comments count
        post.comments_count = Comment.objects.filter(post=post, status="approved").count()

        # Update likes (reactions) count
        post.likes_count = Reaction.objects.filter(object_id=post.id).count()

        post.save(update_fields=["comments_count", "likes_count"])
    except Post.DoesNotExist:
        pass
