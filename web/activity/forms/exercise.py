from activity.models import CodeExercise, CompleteCodeExercise, DiscursiveExercise, Exercise, ExerciseOption
from django import forms
import ast
import re


class SyntaxValidator:
    """Validador de sintaxe de código por linguagem"""
    
    @staticmethod
    def validate_python(code: str) -> bool:
        """Valida sintaxe Python usando ast"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    @staticmethod
    def validate_javascript(code: str) -> bool:
        """Validação básica de JavaScript"""
        # Validação simples: check de braces balanceadas
        try:
            open_braces = code.count('{')
            close_braces = code.count('}')
            open_parens = code.count('(')
            close_parens = code.count(')')
            return open_braces == close_braces and open_parens == close_parens
        except:
            return False
    
    @staticmethod
    def validate_java(code: str) -> bool:
        """Validação básica de Java"""
        required_patterns = [
            r'(public|private|protected)\s+class\s+\w+',
            r'(public|private)\s+static\s+void\s+main',
        ]
        return any(re.search(pattern, code) for pattern in required_patterns)
    
    @staticmethod
    def validate_c(code: str) -> bool:
        """Validação básica de C"""
        # Check para main function e includes básicos
        return 'main' in code and ('{' in code and '}' in code)
    
    @staticmethod
    def validate_cpp(code: str) -> bool:
        """Validação básica de C++"""
        return 'main' in code and ('{' in code and '}' in code)
    
    @classmethod
    def validate(cls, code: str, language: str) -> bool:
        """Valida código na linguagem especificada"""
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
    class Meta:
        model = CodeExercise
        fields = ['language', 'expected_output']
        widgets = {
            'language': forms.RadioSelect(attrs={'class': 'radio-group'}),
            'expected_output': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 10, 'placeholder': 'Saída esperada para correção...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove a opção vazia do campo de turno
        self.fields['language'].choices = [
            choice for choice in self.fields['language'].choices
            if choice[0] != ''
        ]


class CompleteCodeExerciseForm(forms.ModelForm):
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
        starter_code = self.cleaned_data.get('starter_code', '')
        
        if '___' not in starter_code:
            raise forms.ValidationError(
                'O código inicial deve conter "___" para indicar as lacunas que o aluno deve preencher.'
            )
        
        return starter_code
    
    def clean_complete_code(self):
        """Valida a sintaxe do código completo"""
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
    class Meta:
        model = DiscursiveExercise
        fields = ['min_words', 'max_words']
        widgets = {
            'min_words': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número mínimo de palavras'}),
            'max_words': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número máximo de palavras'}),
        }


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['activity_list', 'statement', 'type']
        widgets = {
            'activity_list': forms.HiddenInput(),          
            'type': forms.HiddenInput(),            
            'statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enunciado...'
            }),  
        }


class ExerciseOptionForm(forms.ModelForm):
    class Meta:
        model = ExerciseOption
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Texto da opção'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
