# Generated manually for adding exercise score value.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0008_alter_discursiveexercise_min_words'),
    ]

    operations = [
        migrations.AddField(
            model_name='exercise',
            name='points',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Informe quanto este exercÃ­cio vale na composiÃ§Ã£o da atividade.',
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name='Nota',
            ),
        ),
    ]
