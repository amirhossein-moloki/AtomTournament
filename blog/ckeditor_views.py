from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required

from common.utils.files import get_sanitized_filename
from common.utils.images import convert_image_to_avif
from django.http import HttpResponseForbidden
from .models import Media


@login_required
@csrf_exempt
def ckeditor_upload_view(request):
    # Permission check: User must be staff or an author
    is_author = hasattr(request.user, "author_profile")
    if not (request.user.is_staff or is_author):
        return HttpResponseForbidden("شما اجازه‌ی آپلود فایل را ندارید.")

    if request.method == "POST" and request.FILES.get("upload"):
        uploaded_file = request.FILES["upload"]

        # Check if the uploaded file is an image
        if 'image' not in uploaded_file.content_type:
            return JsonResponse({'error': 'فایل آپلود شده تصویر نیست.'}, status=400)

        # Convert the image to AVIF
        try:
            avif_file = convert_image_to_avif(uploaded_file, quality=60, speed=4)
        except Exception as e:
            return JsonResponse({'error': f'خطا در پردازش تصویر: {e}'}, status=500)

        # Save the converted file using default storage
        sanitized_name = get_sanitized_filename(avif_file.name)
        storage_key = default_storage.save(sanitized_name, avif_file)
        file_url = default_storage.url(storage_key)

        # Create a Media object for the new AVIF image
        media = Media.objects.create(
            storage_key=storage_key,
            url=file_url,
            mime='image/avif',  # Explicitly set the MIME type for AVIF
            size_bytes=avif_file.size,
            title=sanitized_name,
            uploaded_by=request.user,
            type='image'
        )

        # The post_save signal on the Media model will automatically trigger
        # any necessary background processing, like the AVIF conversion task.

        return JsonResponse({'url': file_url})

    return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)
