from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required

from common.utils.images import convert_image_to_avif
from .models import Media
from .tasks import process_media_image

@login_required
@csrf_exempt
def ckeditor_upload_view(request):
    if request.method == 'POST' and request.FILES.get('upload'):
        uploaded_file = request.FILES['upload']

        # Check if the uploaded file is an image
        if 'image' not in uploaded_file.content_type:
            return JsonResponse({'error': 'فایل آپلود شده تصویر نیست.'}, status=400)

        # Convert the image to AVIF
        try:
            avif_file = convert_image_to_avif(uploaded_file)
        except Exception as e:
            return JsonResponse({'error': f'خطا در پردازش تصویر: {e}'}, status=500)

        # Save the converted file using default storage
        storage_key = default_storage.save(avif_file.name, avif_file)
        file_url = default_storage.url(storage_key)

        # Create a Media object for the new AVIF image
        media = Media.objects.create(
            storage_key=storage_key,
            url=file_url,
            mime='image/avif',  # Explicitly set the MIME type for AVIF
            size_bytes=avif_file.size,
            title=avif_file.name,
            uploaded_by=request.user,
            type='image'
        )

        # Trigger the Celery task for image processing if it's an image
        if media.type == 'image':
            process_media_image.delay(media.id)

        return JsonResponse({'url': file_url})

    return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)
