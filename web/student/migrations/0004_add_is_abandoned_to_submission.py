from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0003_add_attempt_number_to_submission'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='is_abandoned',
            field=models.BooleanField(default=False, verbose_name='Abandonada'),
        ),
    ]
