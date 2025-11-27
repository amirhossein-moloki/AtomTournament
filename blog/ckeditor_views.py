from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from .models import Media

@csrf_exempt
def ckeditor_upload_view(request):
    if request.method == 'POST' and request.FILES.get('upload'):
        uploaded_file = request.FILES['upload']

        # Save the file using default storage and create a Media object
        storage_key = default_storage.save(uploaded_file.name, uploaded_file)
        file_url = default_storage.url(storage_key)

        media = Media.objects.create(
            storage_key=storage_key,
            url=file_url,
            mime=uploaded_file.content_type,
            size_bytes=uploaded_file.size,
            title=uploaded_file.name,
            uploaded_by=request.user,
            type='image' if 'image' in uploaded_file.content_type else 'file'
        )

        return JsonResponse({'url': file_url})

    return JsonResponse({'error': 'Invalid request'}, status=400)
