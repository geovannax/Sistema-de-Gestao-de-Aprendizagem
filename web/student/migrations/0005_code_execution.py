import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0019_codeexercise_max_executions'),
        ('student', '0004_add_is_abandoned_to_submission'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_code', models.TextField(verbose_name='Código enviado')),
                ('results', models.JSONField(default=list, verbose_name='Resultados')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Executado em')),
                ('exercise', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='code_executions',
                    to='activity.exercise',
                    verbose_name='Exercício',
                )),
                ('submission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='code_executions',
                    to='student.submission',
                    verbose_name='Submissão',
                )),
            ],
            options={
                'verbose_name': 'Execução de código',
                'verbose_name_plural': 'Execuções de código',
                'ordering': ['-created_at'],
            },
        ),
    ]
