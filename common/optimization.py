import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from celery import shared_task
import subprocess


def optimize_image(image_field):
    """
    Optimizes an image by converting it to AVIF format and compressing it.
    Returns a dictionary with the buffer and the new filename.
    """
    try:
        img = Image.open(image_field)

        # Convert RGBA to RGB if necessary
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # Create a buffer to save the optimized image
        buffer = BytesIO()
        img.save(buffer, format="AVIF", quality=85, optimize=True)
        buffer.seek(0)

        # Get the original filename without extension
        filename = os.path.splitext(image_field.name)[0]
        new_filename = f"{filename}.avif"

        return {"buffer": buffer, "filename": new_filename}

    except Exception as e:
        # Handle exceptions (e.g., corrupted images)
        print(f"Error optimizing image: {e}")
        return None


@shared_task
def optimize_video(video_path):
    """
    Optimizes a video by compressing it using ffmpeg.
    This is a placeholder and needs ffmpeg installed.
    """
    try:
        # Get the original filename without extension
        filename, ext = os.path.splitext(video_path)
        new_filename = f"{filename}_optimized.mp4"

        # Run ffmpeg to compress the video
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vcodec', 'libx264',
            '-crf', '28',
            new_filename
        ]
        subprocess.run(command, check=True)

        # Replace the original file with the optimized one
        os.replace(new_filename, video_path)

    except Exception as e:
        # Handle exceptions (e.g., ffmpeg not installed)
        print(f"Error optimizing video: {e}")
