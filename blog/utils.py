import re

def calculate_reading_time_from_json(content_json):
    """
    Traverses a JSON block structure to extract all text and calculate reading time.
    """
    total_words = 0
    if not isinstance(content_json, list):
        return 0

    for block in content_json:
        if not isinstance(block, dict) or 'data' not in block:
            continue

        data = block.get('data', {})
        text = data.get('text', '')

        # This can be expanded to handle other text-containing fields or block types
        if text and isinstance(text, str):
            words = re.findall(r'\w+', text)
            total_words += len(words)

    reading_time_minutes = total_words / 200  # Average reading speed: 200 WPM
    return int(reading_time_minutes * 60)


def sync_media_attachments_from_json(post_instance):
    """
    Traverses a JSON block structure to find all media IDs and syncs them
    with the PostMedia through model.
    """
    if not hasattr(post_instance, 'content') or not isinstance(post_instance.content, list):
        return

    linked_media_ids = set()
    for block in post_instance.content:
        if isinstance(block, dict) and block.get('type') == 'image':
            media_id = block.get('data', {}).get('media_id')
            if media_id and isinstance(media_id, int):
                linked_media_ids.add(media_id)

    # Add cover and OG images to the set
    if post_instance.cover_media_id:
        linked_media_ids.add(post_instance.cover_media_id)
    if post_instance.og_image_id:
        linked_media_ids.add(post_instance.og_image_id)

    # Sync with the PostMedia model
    current_media_ids = set(
        post_instance.media_attachments.values_list('media_id', flat=True)
    )

    # Add new attachments
    ids_to_add = linked_media_ids - current_media_ids
    for media_id in ids_to_add:
        # Determine attachment_type (this is a simplified logic)
        attachment_type = 'in-content'
        if media_id == post_instance.cover_media_id:
            attachment_type = 'cover'
        elif media_id == post_instance.og_image_id:
            attachment_type = 'og-image'

        post_instance.media_attachments.create(media_id=media_id, attachment_type=attachment_type)

    # Remove old attachments
    ids_to_remove = current_media_ids - linked_media_ids
    post_instance.media_attachments.filter(media_id__in=ids_to_remove).delete()
