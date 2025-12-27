from celery import shared_task
import logging
from notifications.tasks import send_email_notification
from django.db.models import F
from django.core.files.storage import default_storage
from django.conf import settings
from PIL import Image
from common.utils.images import convert_image_to_avif, create_image_variants

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


@shared_task(name="blog.tasks.process_uploaded_media")
def process_uploaded_media(upload_id, user_id, title=None, alt_text=None):
    """
    Asynchronously processes an uploaded media file.
    - Moves it from a temporary location to a permanent one.
    - Optimizes the image and generates variants if it's an image.
    - Creates the Media model instance.
    """
    from .models import Media, User

    storage = default_storage

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found. Aborting media processing for {upload_id}.")
        storage.delete(upload_id)
        return

    if not storage.exists(upload_id):
        logger.error(f"Upload ID {upload_id} does not exist in storage. Aborting.")
        return

    with storage.open(upload_id) as temp_file:
        original_filename = upload_id.split('/')[-1]
        final_storage_key = upload_id.replace(f'tmp/', '')

        media_data = {
            'uploaded_by': user,
            'storage_key': final_storage_key,
            'title': title or original_filename,
            'alt_text': alt_text or '',
            'mime': temp_file.file.content_type,
            'size_bytes': temp_file.size,
        }

        is_image = 'image' in media_data['mime']

        if is_image:
            media_data['type'] = 'image'
            try:
                # Convert to AVIF and create variants
                optimized_file_content, variants = create_image_variants(temp_file)
                storage.save(final_storage_key, optimized_file_content)
                media_data['variants'] = variants
                media_data['url'] = storage.url(final_storage_key)

                # Get dimensions from the main variant
                with Image.open(optimized_file_content) as img:
                    media_data['width'] = img.width
                    media_data['height'] = img.height

            except Exception as e:
                logger.error(f"Failed to process image {upload_id}: {e}")
                storage.save(final_storage_key, temp_file) # Save original file on error
                media_data['url'] = storage.url(final_storage_key)
        else:
            media_data['type'] = 'video' if 'video' in media_data['mime'] else 'file'
            storage.save(final_storage_key, temp_file)
            media_data['url'] = storage.url(final_storage_key)

        Media.objects.create(**media_data)
        logger.info(f"Successfully created Media object for {final_storage_key}")

    storage.delete(upload_id)
    logger.info(f"Deleted temporary file {upload_id}")


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
