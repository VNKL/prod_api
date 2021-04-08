import requests

from django.utils import timezone
from time import sleep

from .models import Account, Proxy


def load_account():
    try:
        account = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=False).first()
    except Exception:
        sleep(1)
        return load_account()
    if account:
        try:
            account.is_busy = True
            account.save()
            return account
        except Exception:
            sleep(1)
            return load_account()
    else:
        try:
            accounts = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=True)
            delta = timezone.timedelta(hours=24)
            for acc in accounts:
                if acc.rate_limit_date + delta > timezone.now():
                    release_account(acc)
                    return acc
        except Exception:
            sleep(1)
            return load_account()

        sleep(300)
        return load_account()


def load_proxy():
    return None
    # try:
    #     proxy = Proxy.objects.filter(is_alive=True, expiration_date__gt=timezone.now(), n_used__lt=5).first()
    # except Exception:
    #     sleep(1)
    #     return load_proxy()
    # if proxy:
    #     proxy_str = f'{proxy.login}:{proxy.password}@{proxy.ip}:{proxy.port}'
    #     if _check_proxy(proxy_str):
    #         try:
    #             proxy.n_used += 1
    #             proxy.save()
    #             return f'{proxy.login}:{proxy.password}@{proxy.ip}:{proxy.port}'
    #         except Exception:
    #             sleep(1)
    #             return load_proxy()
    #     else:
    #         try:
    #             proxy.is_alive = False
    #             proxy.save()
    #             return load_proxy()
    #         except Exception:
    #             return load_proxy()
    # else:
    #     return None


def release_proxy(proxy_str):
    pass
    # proxy_obj = _get_proxy_obj_from_str(proxy_str)
    # if proxy_obj:
    #     try:
    #         proxy_obj.n_used -= 1
    #         proxy_obj.save()
    #     except Exception:
    #         sleep(1)
    #         release_proxy(proxy_str)


def mark_proxy_dead(proxy_str):
    pass
    # proxy_obj = _get_proxy_obj_from_str(proxy_str)
    # if proxy_obj:
    #     try:
    #         proxy_obj.is_alive = False
    #         proxy_obj.n_used -= 1
    #         proxy_obj.save()
    #     except Exception:
    #         sleep(1)
    #         mark_proxy_dead(proxy_str)


def _get_proxy_obj_from_str(proxy_str):
    if proxy_str:
        login_pass, ip_port = proxy_str.split('@')
        login, password = login_pass.split(':')
        ip, port = ip_port.split(':')
        try:
            proxy_obj = Proxy.objects.filter(login=login, password=password, ip=ip, port=port).first()
            return proxy_obj
        except Exception:
            sleep(1)
            return _get_proxy_obj_from_str(proxy_str)


def _check_proxy(proxy_str):
    try:
        proxy_dict = {'http': f'http://{proxy_str}'}
        requests.get('https://www.google.com/', proxies=proxy_dict, timeout=1)
        return True
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        return False


def mark_account_dead(account):
    try:
        account.is_alive = False
        account.is_busy = False
        account.save()
    except Exception:
        sleep(1)
        mark_account_dead(account)


def mark_account_rate_limited(account):
    try:
        account.is_busy = False
        account.is_rate_limited = True
        account.rate_limit_date = timezone.now()
        account.save()
    except Exception:
        sleep(1)
        mark_account_rate_limited(account)


def release_account(account):
    try:
        account.is_busy = False
        account.is_rate_limited = False
        account.save()
    except Exception:
        sleep(1)
        release_account(account)


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
                try:
                    existed_proxy = Proxy.objects.filter(login=login, password=password, ip=ip, port=port).first()
                    if not existed_proxy:
                        proxy_obj = Proxy(login=login, password=password, ip=ip, port=port,
                                          load_date=timezone.now(),
                                          expiration_date=timezone.now() + timezone.timedelta(days=period))
                        proxy_obj.save()
                        return proxy_obj
                    else:
                        return existed_proxy
                except Exception:
                    sleep(1)
                    return create_proxy(proxy, period)


def del_expired_proxy():
    try:
        proxies = Proxy.objects.filter(expiration_date__lt=timezone.now())
        if proxies:
            proxies.delete()
            return {'response': 'proxies was deleted'}
        else:
            return {'response': 'expired proxies are not found'}
    except Exception:
        sleep(1)
        del_expired_proxy()

