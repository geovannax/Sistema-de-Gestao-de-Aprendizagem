from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import FormView
from activity.forms.activity import ActivityForm, ActivityDissertativaForm

# Create your views here.


class ActivityListView(View):
    
    def get(self, request):
        return render(request, 'activity/teste.html')


class ActivityCreateView(FormView):
    template_name = 'activity/create.html'
    form_class = ActivityForm
    success_url = '/activity/create/'

    def form_valid(self, form):
        print(form.cleaned_data)
        #form.save()
        return super().form_valid(form)


class ActivityDissertativaCreateView(FormView):
    template_name = 'activity/create.html'
    form_class = ActivityDissertativaForm
    success_url = '/activity/dissertativa/'

    def form_valid(self, form):
        print(form.cleaned_data)
        return super().form_valid(form)