from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import group.models


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0002_alter_group_description_alter_group_name_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupInvite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(default=group.models.generate_group_invite_token, max_length=128, unique=True)),
                ('expires_at', models.DateTimeField(verbose_name='Expira em')),
                ('max_uses', models.PositiveIntegerField(blank=True, null=True, verbose_name='Limite de usos')),
                ('used_count', models.PositiveIntegerField(default=0, verbose_name='Usos')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Esta ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_group_invites', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invites', to='group.group')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupStudent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True, verbose_name='Entrou em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Esta ativo')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='group.group')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='student_groups', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='groupstudent',
            constraint=models.UniqueConstraint(fields=('group', 'student'), name='unique_group_student'),
        ),
    ]
