from django.contrib import admin

from .models import Analyzer


@admin.register(Analyzer)
class AnalyzerAdmin(admin.ModelAdmin):
    list_display = 'id', 'owner', 'method', 'param', 'status', 'error', 'start_date', 'finish_date'
