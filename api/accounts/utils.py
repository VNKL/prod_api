import requests
import vk_api

from django.utils import timezone
from django import db
from time import sleep
from random import uniform

from .models import Account, Proxy, ProxiesSetting
from vk.audio_savers_new.utils import captcha_handler


def load_account(n_try=0):
    if n_try < 100:

        try:
            db.connections.close_all()
            account = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=False).first()
        except Exception:
            sleep(1)
            db.connections.close_all()
            return load_account(n_try=n_try + 1)
        if account:
            try:
                account.is_busy = True
                account.save()
                db.connections.close_all()
                return account
            except Exception:
                sleep(1)
                return load_account(n_try=n_try + 1)
        else:
            try:
                db.connections.close_all()
                accounts = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=True)
                delta = timezone.timedelta(hours=1)
                for acc in accounts:
                    if acc.rate_limit_date + delta < timezone.now():
                        release_account(acc)
                        acc.is_busy = True
                        acc.save()
                        db.connections.close_all()
                        return acc
            except Exception:
                sleep(1)
                db.connections.close_all()
                return load_account(n_try=n_try + 1)

            sleep(15)
            db.connections.close_all()
            return load_account(n_try=n_try + 1)


def _get_vk_auth_cookies(login, password):
    vk_session = vk_api.VkApi(login=login, password=password, captcha_handler=captcha_handler)
    try:
        vk_session.auth()
        cookies = vk_session.http.cookies.get_dict()
        return cookies
    except vk_api.exceptions.BadPassword as error_msg:
        print(login, password, error_msg)
        return None
    except vk_api.AuthError as error_msg:
        print(login, password, error_msg)
        if error_msg == 'Bad password':
            return None
        sleep(uniform(3, 5))
        return _get_vk_auth_cookies(login, password)


def load_cookies(n_try=0):
    print('load cookies...')
    if n_try < 5:
        try:
            db.connections.close_all()
            account = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=False).first()
        except Exception:
            sleep(1)
            db.connections.close_all()
            return load_account(n_try=n_try + 1)
        if account:
            try:
                cookies = _get_vk_auth_cookies(login=account.login, password=account.password)
                if cookies:
                    account.is_busy = True
                    account.save()
                    db.connections.close_all()
                    return cookies, account
                else:
                    mark_account_dead(account)
                    return load_cookies(n_try=n_try)
            except Exception as err_msg:
                print('!!! error with _get_cookies_from_vk:', err_msg)
                db.connections.close_all()
                return load_account(n_try=n_try+1)

        else:
            db.connections.close_all()
            accounts = Account.objects.filter(is_alive=True, is_busy=False, is_rate_limited=True)
            delta = timezone.timedelta(hours=24)
            for acc in accounts:
                if acc.rate_limit_date + delta > timezone.now():
                    release_account(acc)
                    cookies = _get_vk_auth_cookies(login=account.login, password=account.password)
                    if cookies:
                        acc.is_busy = True
                        acc.save()
                        db.connections.close_all()
                        return cookies, acc
                    else:
                        mark_account_dead(account)
                        return load_cookies(n_try=n_try)

    db.connections.close_all()
    return None, None


def load_proxy():
    print('load proxies...')
    try:
        proxies_settings = ProxiesSetting.objects.filter().first()
        max_n_used = proxies_settings.max_n_used if proxies_settings else 100500
        proxy = Proxy.objects.filter(is_alive=True, expiration_date__gt=timezone.now(), n_used__lt=max_n_used).first()
    except Exception as err_msg:
        print(err_msg)
        sleep(1)
        return load_proxy()
    if proxy:
        proxy_str = f'{proxy.login}:{proxy.password}@{proxy.ip}:{proxy.port}'
        if _check_proxy(proxy_str):
            try:
                proxy.n_used += 1
                proxy.save()
                return f'{proxy.login}:{proxy.password}@{proxy.ip}:{proxy.port}'
            except Exception:
                sleep(1)
                return load_proxy()
        else:
            try:
                proxy.is_alive = False
                proxy.save()
                return load_proxy()
            except Exception:
                return load_proxy()
    else:
        return None


def load_user_agent(n_try=0):
    pass
    # if n_try < 5:
    #     try:
    #         ua = UserAgent.objects.filter().first()
    #         if ua:
    #             return ua.user_agent
    #         else:
    #             return load_user_agent(n_try=n_try+1)
    #     except Exception:
    #         return load_user_agent(n_try=n_try+1)
    # else:
    #     return DEFAULT_USER_AGENT


def release_proxy(proxy_str):
    if proxy_str:
        proxy_obj = _get_proxy_obj_from_str(proxy_str)
        if proxy_obj:
            try:
                proxy_obj.n_used -= 1
                proxy_obj.save()
            except Exception:
                sleep(1)
                release_proxy(proxy_str)


def mark_proxy_dead(proxy_str):
    if proxy_str:
        proxy_obj = _get_proxy_obj_from_str(proxy_str)
        if proxy_obj:
            try:
                proxy_obj.is_alive = False
                proxy_obj.n_used -= 1
                proxy_obj.save()
            except Exception:
                sleep(1)
                mark_proxy_dead(proxy_str)


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
        proxy_dict = {'https': f'http://{proxy_str}', 'http': f'http://{proxy_str}'}
        requests.get('https://www.vk.com/', proxies=proxy_dict, timeout=1)
        return True
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        return False


def mark_account_dead(account, n_try=0):
    if n_try < 5:
        try:
            account.is_alive = False
            account.is_busy = False
            account.save()
        except Exception:
            sleep(1)
            mark_account_dead(account, n_try=n_try + 1)
    db.connections.close_all()


def mark_account_rate_limited(account, n_try=0):
    print('MARK ACCOUNT RATE LIMITED')
    if n_try < 5:
        try:
            account.is_busy = False
            account.is_rate_limited = True
            account.rate_limit_date = timezone.now()
            account.save()
        except Exception:
            sleep(1)
            mark_account_rate_limited(account, n_try=n_try + 1)
    db.connections.close_all()


def release_account(account, n_try=0):
    if account:
        try:
            db.connections.close_all()
            if n_try < 5:
                try:
                    account.is_busy = False
                    account.is_rate_limited = False
                    account.save()
                except Exception:
                    sleep(1)
                    release_account(account, n_try=n_try + 1)
            db.connections.close_all()
        except TypeError:
            pass


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
                        db.connections.close_all()
                        return proxy_obj
                    else:
                        db.connections.close_all()
                        return existed_proxy
                except Exception:
                    sleep(1)
                    db.connections.close_all()
                    return create_proxy(proxy, period)


def del_expired_proxy():
    try:
        proxies = Proxy.objects.filter(expiration_date__lt=timezone.now())
        if proxies:
            proxies.delete()
            db.connections.close_all()
            return {'response': 'proxies was deleted'}
        else:
            db.connections.close_all()
            return {'response': 'expired proxies are not found'}
    except Exception:
        sleep(1)
        db.connections.close_all()
        del_expired_proxy()


def release_all_proxies(n_used=True, is_alive=True):
    try:
        proxies = Proxy.objects.all()
        for proxy in proxies:
            if n_used:
                proxy.n_used = 0
            if is_alive:
                proxy.is_alive = True
            proxy.save()
        return {'response': 'proxies was released'}
    except Exception:
        sleep(1)
        db.connections.close_all()
        release_all_proxies()
