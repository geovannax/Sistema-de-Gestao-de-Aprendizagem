from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0006_fix_legacy_abandoned_submissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='exerciseanswer',
            name='time_spent_seconds',
            field=models.PositiveIntegerField(default=0, verbose_name='Tempo gasto (s)'),
        ),
    ]
