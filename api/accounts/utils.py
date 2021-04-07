import requests

from django.utils import timezone
from time import sleep

from .models import Account, Proxy


def load_account():
    try:
        account = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=False).first()
    except Exception:
        return load_account()
    if account:
        account.is_busy = True
        account.save()
        return account
    else:
        accounts = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=True)
        delta = timezone.timedelta(hours=24)
        for acc in accounts:
            if acc.rate_limit_date + delta > timezone.now():
                release_account(acc)
                return acc

        sleep(300)
        return load_account()


def load_proxy():
    proxy = Proxy.objects.filter(is_alive=True, expiration_date__gt=timezone.now(), n_used__lt=5).first()
    if proxy:
        proxy_str = f'{proxy.login}:{proxy.password}@{proxy.ip}:{proxy.port}'
        if _check_proxy(proxy_str):
            proxy.n_used += 1
            proxy.save()
            return f'{proxy.login}:{proxy.password}@{proxy.ip}:{proxy.port}'
        else:
            proxy.is_alive = False
            proxy.save()
            return load_proxy()
    else:
        return None


def release_proxy(proxy_str):
    proxy_obj = _get_proxy_obj_from_str(proxy_str)
    if proxy_obj:
        proxy_obj.n_used -= 1
        proxy_obj.save()


def mark_proxy_dead(proxy_str):
    proxy_obj = _get_proxy_obj_from_str(proxy_str)
    if proxy_obj:
        proxy_obj.is_alive = False
        proxy_obj.n_used -= 1
        proxy_obj.save()


def _get_proxy_obj_from_str(proxy_str):
    if proxy_str:
        login_pass, ip_port = proxy_str.split('@')
        login, password = login_pass.split(':')
        ip, port = ip_port.split(':')
        proxy_obj = Proxy.objects.filter(login=login, password=password, ip=ip, port=port).first()
        return proxy_obj


def _check_proxy(proxy_str):
    try:
        proxy_dict = {'http': f'http://{proxy_str}'}
        requests.get('https://www.google.com/', proxies=proxy_dict, timeout=1)
        return True
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        return False


def mark_account_dead(account):
    account.is_alive = False
    account.is_busy = False
    account.save()


def mark_account_rate_limited(account):
    account.is_busy = False
    account.is_rate_limited = True
    account.rate_limit_date = timezone.now()
    account.save()


def release_account(account):
    account.is_busy = False
    account.is_rate_limited = False
    account.save()


def create_proxy(proxy: str, period: int):
    if '@' in proxy:
        login_pass, ip_port = proxy.split('@')
        if ':' in login_pass and ':' in ip_port:
            login, password = login_pass.split(':')
            ip, port = ip_port.split(':')
            try:
                port = int(port)
            except ValueError:
                port = None
            if port and '.' in ip:
                existed_proxy = Proxy.objects.filter(login=login, password=password, ip=ip, port=port).first()
                if not existed_proxy:
                    proxy_obj = Proxy(login=login, password=password, ip=ip, port=port,
                                      load_date=timezone.now(),
                                      expiration_date=timezone.now() + timezone.timedelta(days=period))
                    proxy_obj.save()
                    return proxy_obj
                else:
                    return existed_proxy


def del_expired_proxy():
    proxies = Proxy.objects.filter(expiration_date__lt=timezone.now())
    if proxies:
        proxies.delete()
        return {'response': 'proxies was deleted'}
    else:
        return {'response': 'expired proxies are not found'}
