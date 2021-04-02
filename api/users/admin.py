from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = 'username', 'has_token', \
                   'can_ads', 'can_analyzers', 'can_charts', 'can_grabbers', 'can_parsers', 'can_related'
