from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0010_activitylistgroup_starts_at_ends_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityArchived',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_archived', models.BooleanField(db_index=True, default=True, verbose_name='Arquivado')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Arquivado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('activity_list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='archived_activities', to='activity.activitylist')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='archived_activities', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='activityarchived',
            constraint=models.UniqueConstraint(fields=('activity_list', 'user'), name='unique_activity_archived_user'),
        ),
    ]
