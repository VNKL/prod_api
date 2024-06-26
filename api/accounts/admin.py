from django.contrib import admin

from .models import Account, Proxy, ParsingThreadCount, ProxiesSetting


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = 'login', 'password', 'token', 'user_id', 'is_alive', 'is_busy', 'is_rate_limited', 'rate_limit_date'


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = 'is_alive', 'n_used', 'login', 'password', 'ip', 'port', 'load_date', 'expiration_date'


@admin.register(ParsingThreadCount)
class ParsingThreadCountAdmin(admin.ModelAdmin):
    list_display = 'max_threads', 'offset_param', 'savers_count_max_threads', 'savers_count_division_param'


@admin.register(ProxiesSetting)
class ProxiesSettingAdmin(admin.ModelAdmin):
    list_display = 'max_n_used',
