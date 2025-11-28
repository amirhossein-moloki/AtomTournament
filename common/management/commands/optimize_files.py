from django.core.management.base import BaseCommand
from django.apps import apps
from common.optimization import optimize_image, optimize_video

class Command(BaseCommand):
    help = 'Optimizes all existing images and videos in the project.'

    def handle(self, *args, **options):
        self.stdout.write('Starting file optimization...')

        # List of models and fields to optimize
        models_to_optimize = {
            'tournaments.Rank': ['image'],
            'tournaments.GameImage': ['image'],
            'tournaments.TournamentImage': ['image'],
            'tournaments.Match': ['result_proof'],
            'tournaments.Report': ['evidence'],
            'tournaments.WinnerSubmission': ['video'],
            'verification.Verification': ['id_card_image', 'selfie_image', 'video'],
            'teams.Team': ['team_picture'],
            'support.TicketAttachment': ['file'],
            'users.User': ['profile_picture'],
            'rewards.Prize': ['image'],
            'chat.Attachment': ['file'],
            'blog.Media': ['file'],
        }

        for model_str, field_names in models_to_optimize.items():
            try:
                model = apps.get_model(model_str)
                self.stdout.write(f'Optimizing {model_str}...')

                for obj in model.objects.all():
                    for field_name in field_names:
                        field = getattr(obj, field_name)
                        if field:
                            if hasattr(field, 'path'): # For ImageField and FileField
                                if 'image' in field.file.content_type:
                                    optimize_image(field)
                                    obj.save()
                                elif 'video' in field.file.content_type:
                                    optimize_video.delay(field.path)
                            elif isinstance(field, str) and field.startswith('/media/'): # For blog.Media
                                # This part is tricky as we don't have the file object directly
                                # We'll need to find the file in the storage and optimize it
                                pass

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error optimizing {model_str}: {e}'))

        self.stdout.write(self.style.SUCCESS('File optimization complete.'))
