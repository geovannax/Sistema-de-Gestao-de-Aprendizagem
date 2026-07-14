from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0018_remove_default_max_attempts'),
    ]

    operations = [
        migrations.AddField(
            model_name='codeexercise',
            name='max_executions',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='Limite de execuções',
                help_text='Máximo de vezes que o aluno pode clicar em Executar. Deixe em branco para ilimitado.',
            ),
        ),
    ]
