from django.core.management.base import BaseCommand

from api.accounts.models import Account


class Command(BaseCommand):
    help = 'change password, get valid token and write Account in database'

    def add_arguments(self, parser):
        parser.add_argument('-login', action='store', dest='login', type=str)
        parser.add_argument('-user_id', action='store', dest='user_id', type=int)
        parser.add_argument('-is_busy', action='store', dest='is_busy', type=int)
        parser.add_argument('-is_rate_limited', action='store', dest='is_rate_limited', type=int)
        parser.add_argument('-is_alive', action='store', dest='is_alive', type=int)
        parser.add_argument('-rate_limit_date', action='store', dest='rate_limit_date', type=int)

    def handle(self, *args, **options):
        if options['login'] or options['user_id']:
            reset_one(**options)
        else:
            reset_all(**options)


def reset_all(is_busy=False, is_rate_limited=False, is_alive=False, rate_limit_date=False):

    updated_fields = []
    if is_busy:
        updated_fields.append('is_busy')
    if is_alive:
        updated_fields.append('is_alive')
    if is_rate_limited:
        updated_fields.append('is_rate_limited')
    if rate_limit_date:
        updated_fields.append('rate_limit_date')

    if not updated_fields:
        return {'detail': 'Parameters to update are not recieved'}

    accounts = Account.objects.all()

    updated_accs = []
    for acc in accounts:
        if is_busy:
            acc.is_busy = False
        if is_alive:
            acc.is_alive = False
        if is_rate_limited:
            acc.is_rate_limited = False
        if rate_limit_date:
            acc.rate_limit_date = None
        updated_accs.append(acc)

    Account.objects.bulk_update(updated_accs, fields=updated_fields, batch_size=40)

    return updated_accs


def reset_one(login=None, user_id=None, is_busy=False, is_rate_limited=False, is_alive=False, rate_limit_date=False):
    if login:
        account = Account.objects.filter(login=login).first()
    elif user_id:
        account = Account.objects.filter(login=login).first()
    else:
        return {'details': f'login or user_id required'}

    if account:
        if is_busy:
            account.is_busy = False
        if is_alive:
            account.is_alive = False
        if is_rate_limited:
            account.is_rate_limited = False
        if rate_limit_date:
            account.rate_limit_date = None
        account.save()
        return account

    return {'details': f'Account with {"login" if login else "user_id"} "{login if login else user_id}" is not found'}
