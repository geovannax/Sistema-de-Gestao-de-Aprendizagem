"""Formulários de criação e edição de exercícios.

Contém o formulário base :class:`ExerciseForm`, os formulários específicos
por tipo de exercício e o validador de sintaxe :class:`SyntaxValidator`.
"""
from activity.models import CodeExercise, CodeTestCase, CompleteCodeExercise, DiscursiveExercise, Exercise, ExerciseOption
from django import forms
import ast
import re


class SyntaxValidator:
    """Valida a sintaxe de código-fonte por linguagem de programação."""

    @staticmethod
    def validate_python(code: str) -> bool:
        """Verifica se o código Python é sintaticamente válido usando ``ast``.

        Args:
            code: Código-fonte Python a validar.

        Returns:
            ``True`` se a sintaxe for válida, ``False`` se levantar ``SyntaxError``.
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    @staticmethod
    def validate_javascript(code: str) -> bool:
        """Verifica se chaves e parênteses do código JavaScript estão balanceados.

        Args:
            code: Código-fonte JavaScript a validar.

        Returns:
            ``True`` se chaves e parênteses estiverem balanceados.
        """
        try:
            open_braces = code.count('{')
            close_braces = code.count('}')
            open_parens = code.count('(')
            close_parens = code.count(')')
            return open_braces == close_braces and open_parens == close_parens
        except:  # pragma: no cover
            return False

    @staticmethod
    def validate_java(code: str) -> bool:
        """Verifica se o código Java contém a estrutura mínima esperada.

        Exige declaração de classe e método ``main`` com modificadores de acesso.

        Args:
            code: Código-fonte Java a validar.

        Returns:
            ``True`` se ao menos um dos padrões obrigatórios for encontrado.
        """
        required_patterns = [
            r'(public|private|protected)\s+class\s+\w+',
            r'(public|private)\s+static\s+void\s+main',
        ]
        return any(re.search(pattern, code) for pattern in required_patterns)

    @staticmethod
    def validate_c(code: str) -> bool:
        """Verifica se o código C contém a função ``main`` e chaves.

        Args:
            code: Código-fonte C a validar.

        Returns:
            ``True`` se ``main`` e chaves estiverem presentes.
        """
        return 'main' in code and ('{' in code and '}' in code)

    @staticmethod
    def validate_cpp(code: str) -> bool:
        """Verifica se o código C++ contém a função ``main`` e chaves.

        Args:
            code: Código-fonte C++ a validar.

        Returns:
            ``True`` se ``main`` e chaves estiverem presentes.
        """
        return 'main' in code and ('{' in code and '}' in code)

    @classmethod
    def validate(cls, code: str, language: str) -> bool:
        """Despacha a validação para o método específico da linguagem.

        Args:
            code: Código-fonte a validar.
            language: Identificador da linguagem (``'python'``, ``'javascript'``,
                ``'java'``, ``'c'`` ou ``'cpp'``).

        Returns:
            ``True`` se o código passar na validação da linguagem, ou ``True``
            caso a linguagem não tenha validador registrado.
        """
        validators = {
            'python': cls.validate_python,
            'javascript': cls.validate_javascript,
            'java': cls.validate_java,
            'c': cls.validate_c,
            'cpp': cls.validate_cpp,
        }

        validator = validators.get(language)
        if not validator:
            return True

        return validator(code)


class CodeExerciseForm(forms.ModelForm):
    """Formulário para exercícios do tipo código. Campos: linguagem de programação."""
    class Meta:
        model = CodeExercise
        fields = ['language']
        widgets = {
            'language': forms.RadioSelect(attrs={'class': 'radio-group'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['language'].choices = [
            choice for choice in self.fields['language'].choices
            if choice[0] != ''
        ]


class CodeTestCaseForm(forms.ModelForm):
    """Formulário para um caso de teste de exercício de código."""
    class Meta:
        model = CodeTestCase
        fields = ['input', 'expected_output']
        widgets = {
            'input': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 4,
                'placeholder': 'Ex: 5 3',
            }),
            'expected_output': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 4,
                'placeholder': 'Ex: 4.0',
            }),
        }


class CompleteCodeExerciseForm(forms.ModelForm):
    """Formulário para exercícios do tipo completar código.

    Valida que ``starter_code`` contenha ``___`` (lacunas) e que
    ``complete_code`` não as contenha e passe na validação de sintaxe
    da linguagem selecionada via :class:`SyntaxValidator`.
    """
    class Meta:
        model = CompleteCodeExercise
        fields = ['language', 'starter_code', 'complete_code']
        widgets = {
            'language': forms.RadioSelect(attrs={'class': 'radio-group'}),
            'starter_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 10, 'placeholder': 'Código inicial...'}),
            'complete_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 10, 'placeholder': 'Código completo...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove a opção vazia do campo de turno
        self.fields['language'].choices = [
            choice for choice in self.fields['language'].choices
            if choice[0] != ''
        ]

    def clean_starter_code(self):
        """Valida que o código inicial contenha ao menos uma lacuna ``___``.

        Raises:
            ValidationError: Se ``___`` não estiver presente no código.
        """
        starter_code = self.cleaned_data.get('starter_code', '')

        if '___' not in starter_code:
            raise forms.ValidationError(
                'O código inicial deve conter "___" para indicar as lacunas que o aluno deve preencher.'
            )

        return starter_code

    def clean_complete_code(self):
        """Valida a sintaxe e a integridade do código completo (gabarito).

        Raises:
            ValidationError: Se ``___`` estiver presente no gabarito ou se a
                sintaxe for inválida para a linguagem selecionada.
        """
        complete_code = self.cleaned_data.get('complete_code', '')
        language = self.cleaned_data.get('language', '')

        # O complete_code NÃO deve conter '___'
        if '___' in complete_code:
            raise forms.ValidationError(
                'O código completo não deve conter "___". Substitua todos os espaços em branco por código real.'
            )

        if language and complete_code:
            if not SyntaxValidator.validate(complete_code, language):
                raise forms.ValidationError(
                    f'O código contém erros de sintaxe para {language}. Verifique e tente novamente.'
                )

        return complete_code


class DiscursiveExerciseForm(forms.ModelForm):
    """Formulário para exercícios discursivos.

    Campos: quantidade mínima e máxima de palavras exigida na resposta.
    """
    class Meta:
        model = DiscursiveExercise
        fields = ['min_words', 'max_words']
        widgets = {
            'min_words': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número mínimo de palavras'}),
            'max_words': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número máximo de palavras'}),
        }


class ExerciseForm(forms.ModelForm):
    """Formulário base para criação e edição de exercícios.

    Os campos ``activity_list`` e ``type`` são ocultos e preenchidos
    automaticamente pelo mixin :class:`~activity.mixins.ExerciseBaseMixin`
    via ``get_initial()``.
    """
    class Meta:
        model = Exercise
        fields = ['activity_list', 'statement', 'points', 'type']
        widgets = {
            'activity_list': forms.HiddenInput(),
            'type': forms.HiddenInput(),
            'statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enunciado...'
            }),
            'points': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.5',
                'placeholder': 'Ex: 1.00'
            }),
        }


class ExerciseOptionForm(forms.ModelForm):
    """Formulário para uma alternativa de exercício de múltipla escolha.

    Usado dentro do formset :data:`~activity.forms.formsets.exercise_option.ExerciseOptionFormCreateSet`
    e :data:`~activity.forms.formsets.exercise_option.ExerciseOptionFormUpdateSet`.
    """
    class Meta:
        model = ExerciseOption
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Texto da opção'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
