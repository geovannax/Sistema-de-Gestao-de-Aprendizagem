from activity.forms.exercise import ExerciseOptionForm
from activity.models import ExerciseOption, MultipleChoiceExercise
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory


class BaseExerciseOptionFormSet(BaseInlineFormSet):
    def clean(self):
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


ExerciseOptionFormUpdateSet = inlineformset_factory(
    MultipleChoiceExercise,
    ExerciseOption,
    form=ExerciseOptionForm,
    formset=BaseExerciseOptionFormSet,
    extra=0,
    can_delete=True
)