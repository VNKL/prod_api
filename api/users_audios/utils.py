from django.utils import timezone

from .models import Parser


def create_parser(user, data):
    parser = Parser(owner=user,
                    status=3,
                    start_date=timezone.now(),
                    name=data['name'],
                    n_last=data['n_last'] if data['n_last'] < 100 else 100,
                    type=data['type'],
                    user_ids=data['user_ids'])
    parser.save()
    return {'parser_id': parser.pk}


def delete_parser(user, data):
    parser = Parser.objects.filter(owner=user, pk=data['id']).first()
    if not parser:
        return {'error': f'not found or no permissions to users audios parser with id {data["id"]}'}

    parser.delete()
    return {'response': f" users audios parser with id {data['id']} was deleted"}


def users_audios_results_to_csv_filename(parser):
    return f"{parser['name']} ({parser['start_date']}).csv"


def users_audios_results_to_filebody(parser):
    header = 'Артист или трек\tУ скольки пользователей добавлен\tДоля среди добавлений всех пользователей\n'
    if 'items' in parser.keys():
        for item in parser['items']:
            header += f"{item['name']}\t" \
                      f"{item['share_users'] * 100} %\t" \
                      f"{item['share_items'] * 100} %\n"
    return header
