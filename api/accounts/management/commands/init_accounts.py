from django.core.management.base import BaseCommand
from django import db

from api.accounts.models import Account


class Command(BaseCommand):
    help = 'init admin'

    def handle(self, *args, **options):
        existed_accs = Account.objects.all()
        existed_logins = [x.login for x in existed_accs]
        csv_accs = open_csv()
        new_accs = []
        for acc in csv_accs:
            login, password, token, user_id = acc
            if login not in existed_logins:
                new_acc = Account(login=login, password=password, token=token, user_id=user_id)
                new_accs.append(new_acc)

        if new_accs:
            Account.objects.bulk_create(new_accs, batch_size=40)
            db.connections.close_all()


def open_csv():
    with open('accounts.csv') as file:
        lines = file.read().rstrip().split('\n')
        return [x.split(';') for x in lines]
