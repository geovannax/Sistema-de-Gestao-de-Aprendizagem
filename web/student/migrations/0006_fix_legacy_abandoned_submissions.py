"""
Corrige submissões legadas que foram abandonadas (reload/reconnect) mas ficaram
com is_abandoned=False porque o campo não existia quando foram fechadas.

Critérios para marcar como abandonada:
  1. submitted_at is not null, is_abandoned=False
  2. E pelo menos uma das condições:
     a) Existe uma submissão mais recente do mesmo aluno na mesma atividade
        (attempt_number maior) → foi substituída por um novo acesso
     b) Não possui nenhuma resposta (ExerciseAnswer) → nunca foi usada de verdade
"""
from django.db import migrations


def fix_abandoned(apps, schema_editor):
    Submission = apps.get_model('student', 'Submission')
    ExerciseAnswer = apps.get_model('student', 'ExerciseAnswer')

    candidates = Submission.objects.filter(
        submitted_at__isnull=False,
        is_abandoned=False,
    ).order_by('student_id', 'activity_link_id', 'attempt_number')

    answered_sub_ids = set(
        ExerciseAnswer.objects.values_list('submission_id', flat=True).distinct()
    )

    to_abandon = []

    seen: dict[tuple, int] = {}  # (student_id, activity_link_id) -> max attempt_number seen so far

    # Two-pass: first collect max attempt_number per (student, link)
    max_attempt: dict[tuple, int] = {}
    for sub in candidates:
        key = (sub.student_id, sub.activity_link_id)
        if key not in max_attempt or sub.attempt_number > max_attempt[key]:
            max_attempt[key] = sub.attempt_number

    for sub in candidates:
        key = (sub.student_id, sub.activity_link_id)
        has_newer = sub.attempt_number < max_attempt[key]
        has_answers = sub.pk in answered_sub_ids

        if has_newer or not has_answers:
            to_abandon.append(sub.pk)

    if to_abandon:
        Submission.objects.filter(pk__in=to_abandon).update(is_abandoned=True)


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0005_code_execution'),
    ]

    operations = [
        migrations.RunPython(fix_abandoned, migrations.RunPython.noop),
    ]
