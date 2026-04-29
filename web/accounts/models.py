from django.db import models
from django.contrib.auth.models import User


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    # Tudo em um JSON - sem migrações futuras!
    preferences = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Seu modelo UserPreferences tem:
    def set_view_type(self, cookie_key, view_type):
        """Define preferência de view_type"""
        if 'view_type' not in self.preferences:
            self.preferences['view_type'] = {}
        self.preferences['view_type'][cookie_key] = view_type
        self.save()


