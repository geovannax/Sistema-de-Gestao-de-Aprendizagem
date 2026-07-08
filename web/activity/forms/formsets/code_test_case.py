"""Formsets para gerenciamento de casos de teste de exercícios de código."""
from activity.forms.exercise import CodeTestCaseForm
from activity.models import CodeExercise, CodeTestCase
from django.forms import inlineformset_factory


CodeTestCaseFormCreateSet = inlineformset_factory(
    CodeExercise,
    CodeTestCase,
    form=CodeTestCaseForm,
    extra=2,
    can_delete=True,
)
"""Formset de criação com 2 casos extras e suporte a exclusão."""

CodeTestCaseFormUpdateSet = inlineformset_factory(
    CodeExercise,
    CodeTestCase,
    form=CodeTestCaseForm,
    extra=0,
    can_delete=True,
)
"""Formset de edição sem casos extras — novos casos são adicionados via botão."""
