from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0010_populate_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='slug',
            field=models.SlugField(max_length=150, unique=True),
        ),
        migrations.AlterField(
            model_name='tournament',
            name='slug',
            field=models.SlugField(max_length=150, unique=True),
        ),
    ]
