from celery import shared_task
import logging
from notifications.tasks import send_email_notification
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


from common.utils.images import convert_image_to_avif

from django.core.files.storage import default_storage

@shared_task
def process_media_image(media_id):
    """
    Celery task to process an uploaded image, including converting to AVIF.
    """
    from .models import Media
    try:
        media = Media.objects.get(id=media_id)
        if "image" in media.mime and not media.storage_key.lower().endswith(".avif"):
            original_storage_key = media.storage_key
            try:
                # Assuming media.storage_key is the path to the file
                avif_file = convert_image_to_avif(media.storage_key)

                # Update the media object with the new AVIF file details
                media.storage_key = avif_file.name
                media.mime = "image/avif"
                media.url = default_storage.url(avif_file.name)
                media.size_bytes = avif_file.size
                media.save()

                # Delete the original file
                default_storage.delete(original_storage_key)

                logger.info(f"Successfully converted image to AVIF for media: {media.title}")

            except Exception as e:
                logger.error(f"Error converting image to AVIF for media ID {media_id}: {e}")
    except Media.DoesNotExist:
        logger.error(f"Media with id {media_id} not found for processing.")


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
