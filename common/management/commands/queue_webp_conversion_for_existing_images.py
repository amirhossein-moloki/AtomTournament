from django.core.management.base import BaseCommand
from django.apps import apps
from common.tasks import convert_image_to_webp_task

class Command(BaseCommand):
    help = 'Queues a Celery task to convert all existing images to WebP format.'

    # Define the models and their respective image fields to be processed
    MODELS_AND_FIELDS = {
        'chat.Attachment': ['file'],
        'verification.Verification': ['id_card_image', 'selfie_image'],
        'teams.Team': ['team_picture'],
        'support.TicketAttachment': ['file'],
        'users.User': ['profile_picture'],
        'rewards.Prize': ['image'],
        'tournaments.Rank': ['image'],
        'tournaments.GameImage': ['image'],
        'tournaments.TournamentImage': ['image'],
        'tournaments.Match': ['result_proof'],
        'tournaments.Report': ['evidence'],
    }

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to queue WebP conversion tasks for existing images...'))

        for model_str, field_names in self.MODELS_AND_FIELDS.items():
            try:
                app_label, model_name = model_str.split('.')
                Model = apps.get_model(app_label, model_name)
                self.stdout.write(f'Processing model: {model_name}')

                # Query all instances of the model
                instances = Model.objects.all()

                for instance in instances:
                    for field_name in field_names:
                        image_field = getattr(instance, field_name)

                        # Check if the image field has a file and it's not already a WebP
                        if image_field and hasattr(image_field, 'name') and image_field.name and not image_field.name.lower().endswith('.webp'):
                            self.stdout.write(f'  - Queuing task for {model_name} pk={instance.pk}, field={field_name}')
                            convert_image_to_webp_task.delay(
                                app_label=app_label,
                                model_name=model_name,
                                instance_pk=instance.pk,
                                field_name=field_name
                            )

            except LookupError:
                self.stdout.write(self.style.WARNING(f'Could not find model: {model_str}. Skipping.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An error occurred while processing {model_str}: {e}'))

        self.stdout.write(self.style.SUCCESS('Finished queuing all tasks.'))
