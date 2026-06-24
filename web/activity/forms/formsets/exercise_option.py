"""Formsets para gerenciamento de alternativas de exercícios de múltipla escolha."""
from activity.forms.exercise import ExerciseOptionForm
from activity.models import ExerciseOption, MultipleChoiceExercise
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory


class BaseExerciseOptionFormSet(BaseInlineFormSet):
    """Formset base para alternativas de múltipla escolha.

    Garante que exatamente uma alternativa seja marcada como correta.
    Levanta ``ValidationError`` se nenhuma ou mais de uma estiver marcada.
    """

    def clean(self) -> None:
        """Valida que exatamente uma alternativa esteja marcada como correta.

        Raises:
            ValidationError: Se nenhuma alternativa for correta ou se mais
                de uma for marcada como correta.
        """
        super().clean()

        # evita validar duas vezes
        if any(self.errors):
            return  # pragma: no cover

        correct_count = 0

        for form in self.forms:
            if form.cleaned_data.get('DELETE'):  # pragma: no cover
                continue

            # Usa form.data em vez de cleaned_data
            if form.data.get(f'{form.prefix}-is_correct'):
                correct_count += 1

        if correct_count == 0:
            raise ValidationError('Selecione a alternativa correta.')
        elif correct_count > 1:
            raise ValidationError('Apenas uma alternativa pode ser correta.')


ExerciseOptionFormCreateSet = inlineformset_factory(
    MultipleChoiceExercise,
    ExerciseOption,
    form=ExerciseOptionForm,
    formset=BaseExerciseOptionFormSet,
    extra=3,
    can_delete=True
)
"""Formset de criação com 3 alternativas extras e suporte a exclusão."""

ExerciseOptionFormUpdateSet = inlineformset_factory(
    MultipleChoiceExercise,
    ExerciseOption,
    form=ExerciseOptionForm,
    formset=BaseExerciseOptionFormSet,
    extra=0,
    can_delete=True
)
"""Formset de edição sem alternativas extras e com suporte a exclusão."""
