from celery import shared_task
import logging
from notifications.tasks import send_email_notification
from django.utils import timezone
from django.db.models import F

logger = logging.getLogger(__name__)


@shared_task
def increment_post_view_count(post_id):
    """
    Asynchronously increments the view count for a given post.
    """
    from .models import Post
    try:
        Post.objects.filter(pk=post_id).update(views_count=F('views_count') + 1)
        logger.info(f"Incremented view count for Post ID: {post_id}")
    except Exception as e:
        logger.error(f"Error incrementing view count for Post ID {post_id}: {e}")


@shared_task
def notify_author_on_new_comment(comment_id):
    """
    Celery task to send a notification to the post author about a new comment.
    """
    from .models import Comment
    try:
        comment = Comment.objects.select_related('post', 'post__author', 'post__author__user').get(id=comment_id)
        post_author = comment.post.author.user

        if post_author.email:
            send_email_notification.delay(
                recipient_email=post_author.email,
                subject=f"New comment on your post '{comment.post.title}'",
                template_name="notifications/email/new_comment_notification.html",
                context={
                    "post_title": comment.post.title,
                    "commenter_name": comment.author_name or "An anonymous user",
                    "comment_content": comment.content,
                },
            )
    except Comment.DoesNotExist:
        logger.error(f"Comment with id {comment_id} not found for notification task.")


@shared_task
def publish_scheduled_posts():
    """
    Publish posts that were scheduled for a time in the past.
    """
    from .models import Post
    now = timezone.now()
    posts_to_publish = Post.objects.filter(
        status='scheduled',
        scheduled_at__lte=now
    )

    if posts_to_publish.exists():
        num_published = posts_to_publish.update(
            status='published',
            published_at=F('scheduled_at'),
            scheduled_at=None
        )
        logger.info(f"Successfully published {num_published} scheduled posts.")
    else:
        logger.info("No scheduled posts to publish.")
