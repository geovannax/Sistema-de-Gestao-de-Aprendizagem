# Generated manually for activity availability period.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0009_exercise_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitylistgroup',
            name='starts_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='InÃ­cio'),
        ),
        migrations.AddField(
            model_name='activitylistgroup',
            name='ends_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fim'),
        ),
    ]
