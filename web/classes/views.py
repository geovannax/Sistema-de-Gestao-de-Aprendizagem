from django import forms
from django.contrib import messages
from django.views.generic import CreateView, ListView
from classes.models import Classes


class ClassesListView(ListView):
    model = Classes
    template_name = 'classes/list.html'
    context_object_name = 'classes'
    paginate_by = 10
    ordering = ['-id']


class ClassesCreateView(CreateView):
    model = Classes
    template_name = 'global/partials/form.html'
    fields = ['name', 'description']
    success_url = '/classes/list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': 'Criar Turma',
            'submit_title': 'Cadastrar Turma'
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Turma criada com sucesso!')
        messages.error(self.request, 'Turma criada com sucesso!')
        messages.warning(self.request, 'Turma criada com sucesso!')
        messages.info(self.request, 'Turma criada com sucesso!')
        return response

    def get_form_class(self):
        form_class = super().get_form_class()
        form_class.base_fields['name'].label = 'Nome da Turma'
        form_class.base_fields['name'].widget = forms.TextInput(attrs={
            'class': 'form-control py-3',
            'placeholder': 'Nome'
        })
        form_class.base_fields['description'].label = 'Descrição'
        form_class.base_fields['description'].widget = forms.Textarea(attrs={
            'class': 'form-control py-3',
            'rows': 5
        })
        return form_class
