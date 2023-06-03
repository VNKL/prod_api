import os
import shutil
from django.core.management.base import BaseCommand

from api.parsers.models import Parser


class Command(BaseCommand):
    help = 'start parsing with selected method'

    def add_arguments(self, parser):
        parser.add_argument('-parser_id', action='store', dest='parser_id', type=int)

    def handle(self, *args, **options):
        if 'parser_id' not in options.keys():
            print('parser_id is required to start_parser command')
        else:
            start_parser()


def start_parser():

    # parsers = Parser.objects.filter(count_only=False, status=2)
    # count = len(parsers)
    # dir_name = 'parsing_results/bases'
    # os.makedirs(dir_name, exist_ok=True)
    # for n, parser in enumerate(parsers):
    #     try:
    #         src = parser.result_path
    #         name = src[16:]
    #         dst = f'parsing_results/bases/{name}'
    #         shutil.copyfile(src, dst)
    #         print(f'{n+1} / {count} \t | \t {name}')
    #     except Exception:
    #         print(f'{n + 1} / {count} \t | ERROR')

    shutil.make_archive('parsing_results/bases', 'zip', 'parsing_results/bases')
    print('done')
