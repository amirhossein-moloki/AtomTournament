from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_customattachment_ckeditor_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customattachment",
            name="name",
            field=models.CharField(max_length=255, blank=True),
        ),
    ]
