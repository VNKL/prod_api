import os
import shutil
import zipfile
import pytz

from collections import Counter
from datetime import datetime

from django.utils import timezone
from django import db

from .models import Parser, Audio
from vk.audio_savers.utils import pars_post_id_from_post_url
from api.settings import CORE_AUDIO_OWNERS


def create_parser(user, data):
    data['count_only'] = True   # Теперь невозможно парсить айдишки, только количество

    available_sources = ['artist_url', 'track_name', 'group', 'playlist', 'post', 'chart', 'new_releases', 'newsfeed',
                         'parser', 'audio']
    method = 'get_by_'
    param = None

    for source, param in data.items():
        if source in available_sources and param:
            method += source
            param = param
            break

    method = 'get_by_chart' if method == 'get_by_' else method

    parser = Parser(owner=user,
                    status=3,
                    method=method,
                    param=param,
                    count_only=data['count_only'],
                    start_date=timezone.now())
    parser.save()
    db.connections.close_all()
    return {'parser_id': parser.pk}


def delete_parser(user, data):
    parser = Parser.objects.filter(owner=user, pk=data['id']).first()
    if not parser:
        db.connections.close_all()
        return {'error': f'not found or no permissions to parser with id {data["id"]}'}

    zip_path = parser.result_path
    if zip_path:
        os.remove(zip_path)

    parser.delete()
    db.connections.close_all()
    return {'response': f"parser with id {data['id']} was deleted"}


def save_parsing_result(parser, result):
    audio_objects = []
    for audio in result:
        audio = _refactor_parsed_audio_format(audio)
        audio = _create_audio_obj(audio, parser)
        audio_objects.append(audio)

    if audio_objects:
        Audio.objects.bulk_create(audio_objects, batch_size=40)
        parser.savers_count = _len_parser_savers_count(audio_objects)
        parser.audios_count = len(audio_objects)
        parser.save()
        parser.result_path = _dump_savers_results(parser, result)
        parser.status = 2
        parser.finish_date = timezone.now()
        parser.save()
        db.connections.close_all()
    else:
        db.connections.close_all()
        _save_results_error(parser)


def _dump_savers_results(parser, result):
    if parser and result:
        saves_from, saves_exact, audios_as_list, total_count, unique_count = _process_savers_result(result)

        title = _get_parser_title(parser)
        title = del_bad_symbols_from_name(title)
        datetime_now = str(datetime.now()).split('.')[0].replace(':', '-')
        core_path = f'parsing_results/{title} ({datetime_now})'
        os.makedirs(core_path, exist_ok=True)

        _write_saves_by_tracks(result, core_path)
        _write_saves_from(saves_from, core_path)
        _write_saves_exact(saves_exact, core_path)
        _write_top_audios(audios_as_list, core_path, total_count, unique_count, title)
        zip_result_path = _zip_dir(core_path)

        shutil.rmtree(core_path, ignore_errors=True)

        return zip_result_path


def _get_parser_title(parser):
    method = parser.method
    param = parser.param
    title = 'unknown source'

    if method == 'get_by_artist_url':
        title = param.replace('https://vk.com/artist/', '')

    elif method == 'get_by_track_name':
        title = param

    elif method == 'get_by_group':
        title = f"group {param.replace('https://vk.com/', '')}" if 'https://vk.com/' in param else f'group {param}'

    elif method == 'get_by_playlist':
        if 'playlist' in param:
            title = f"playlist {param.replace('https://vk.com/music/playlist/', '')}"
        elif 'album' in param:
            title = f"album {param.replace('https://vk.com/music/album/', '')}"

    elif method == 'get_by_newsfeed':
        title = f'newsfeed by query "{param}"'

    elif method == 'get_by_post':
        title = f'post wall{pars_post_id_from_post_url(param)}'

    elif method == 'get_by_chart':
        title = 'chart'

    elif method == 'get_by_new_releases':
        title = 'new releases'

    elif method == 'get_by_parser':
        old_parser = Parser.objects.filter(pk=param).first()
        if old_parser:
            return _get_parser_title(old_parser)
        else:
            title = f'parser_{param} updated results'

    elif method == 'get_by_audio':
        audio = Audio.objects.filter(pk=param).first()
        if audio:
            title = f'{audio.artist} - {audio.title} [pre-parsed audio savers]'
        else:
            title = '[pre-parsed audio savers]'

    return title


def del_bad_symbols_from_name(name):
    for x in ['/', ':', '*', '"', '<', '>', '|']:
        name = name.replace(x, ' ')

    if len(name) > 30:
        name = name[:30]

    return name


def _write_saves_by_tracks(audios, core_path):
    folder_path = f'{core_path}/tracks'
    os.makedirs(folder_path, exist_ok=True)
    for audio in audios:
        if 'savers' in audio.keys() and audio['savers']:
            title = audio['title']
            if 'subtitle' in audio.keys() and audio['subtitle'] and 'feat.' not in audio['subtitle']:
                title += f" ({audio['subtitle']})"
            title = del_bad_symbols_from_name(title)
            artist = audio['artist']
            artist = del_bad_symbols_from_name(artist)
            audio_folder_path = f"{folder_path}/{artist} - {title}"
            os.makedirs(audio_folder_path, exist_ok=True)
            file_title = f"{audio_folder_path}/{artist} - {title} ({len(audio['savers'])})"
            _write_sliced_txt(file_title, audio['savers'])


def _write_saves_from(saves_from, core_path):
    folder_path = f'{core_path}/from'
    os.makedirs(folder_path, exist_ok=True)
    for count, user_ids in saves_from.items():
        if count > 15:
            break
        file_title = f'{folder_path}/{count} and more audios ({len(user_ids)})'
        _write_sliced_txt(file_title, user_ids)


def _write_saves_exact(saves_exact, core_path):
    folder_path = f'{core_path}/exact'
    os.makedirs(folder_path, exist_ok=True)
    for count, user_ids in saves_exact.items():
        if count == 1:
            file_title = f'{folder_path}/{count} audio ({len(user_ids)})'
        else:
            file_title = f'{folder_path}/{count} audios ({len(user_ids)})'
        _write_sliced_txt(file_title, user_ids)


def _write_top_audios(audios_as_list, core_path, total_count, unique_count, title):
    unique_audios = {}
    for x in audios_as_list:
        saves_count = x[0]
        audio_id = x[1].lower()
        if audio_id not in unique_audios.keys():
            unique_audios[audio_id] = saves_count
        else:
            unique_audios[audio_id] += saves_count

    unique_audios_list = [[val, key] for key, val in unique_audios.items()]
    unique_audios_list.sort(reverse=True)

    with open(f'{core_path}/top audios.txt', 'w', encoding='utf-16') as file:

        n_top = 100 if len(unique_audios_list) >= 100 else len(unique_audios_list)

        file.write(f'{title}\n\n')
        file.write(f'total savers count: {total_count}\n')
        file.write(f'unique savers count: {unique_count}\n\n')
        file.write(f'top-{n_top} audios by savers count:\n')

        for n, audio in enumerate(unique_audios_list[:n_top]):
            file.write(f'{n + 1}) {audio[1]}   ({audio[0]})\n')


def _write_sliced_txt(file_title, user_ids):
    limit_b = 20000000
    n = 1
    path = f'{file_title} [{n}].txt'
    file = open(path, 'a')
    n_ids = len(user_ids)
    for x in range(0, n_ids, 10000):
        y = x + 10000 if x + 10000 <= n_ids else None
        batch = [str(x) for x in user_ids[x:y]]
        if os.stat(path).st_size + 200000 < limit_b:
            file.write('\n'.join(batch))
            file.write('\n')
        else:
            file.close()
            n += 1
            path = f'{file_title} [{n}].txt'
            file = open(path, 'a')
            file.write('\n'.join(batch))
            file.write('\n')
    file.close()


def _zip_dir(core_path):
    zip_path = f'{core_path}.zip'

    zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(core_path):
        for file in files:
            zipf.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(core_path, '..')))
    zipf.close()

    return zip_path


def _process_savers_result(audios):
    total_count = 0
    all_savers = []
    audios_as_list = []
    for audio in audios:
        audios_as_list.append([audio['savers_count'] if 'savers_count' in audio.keys() else 0,
                               f'{audio["artist"]} - {audio["title"]}',
                               f'{audio["owner_id"]}_{audio["audio_id"]}'])
        total_count += audio['savers_count'] if 'savers_count' in audio.keys() else 0
        if 'savers' in audio.keys():
            all_savers.extend(audio['savers'])

    counter = Counter(all_savers)
    unique_count = len(counter.keys())
    counter_values = set(counter.values())
    saves_from = {x: [] for x in counter_values}
    saves_exact = {x: [] for x in counter_values}
    for user_id, saves_count in counter.items():
        saves_exact[saves_count].append(user_id)
        for val in counter_values:
            if val <= saves_count:
                saves_from[val].append(user_id)

    if not unique_count:
        unique_count = 'unknown'

    return saves_from, saves_exact, audios_as_list, total_count, unique_count


def _len_parser_savers_count(audio_objects):
    savers_count = 0
    for audio in audio_objects:
        savers_count += audio.savers_count
    return savers_count


def _create_audio_obj(audio, parser):
    audio = audio.copy()
    audio.pop('savers', None)
    new_audio = Audio(parser=parser, **audio)
    db.connections.close_all()
    return new_audio


def _save_results_error(parser):
    parser.status = 0
    parser.error = 'Error with saving results'
    parser.finish_date = timezone.now()
    parser.save()
    db.connections.close_all()


def _refactor_parsed_audio_format(audio):
    audio = audio.copy()

    audio['parsing_date'] = timezone.now()

    if 'date' in audio.keys():
        d = datetime.fromtimestamp(audio['date']).replace(tzinfo=pytz.utc) if isinstance(audio['date'], int) else audio['date']
        audio['date'] = d

    return audio


def parsing_results_to_csv_filename(parser):
    title = parser['result_path'].split('/')[-1].replace('.zip', '.csv')
    return title


def parsing_results_to_filebody(parser):
    header = 'МБО\tИсполнитель\tНазвание\tИсточник добавления\tКоличество добавлений\tСсылка на пост\n'
    for audio in parser['audios']:
        mbo = 'Да' if str(audio['owner_id'])[:4] in CORE_AUDIO_OWNERS else 'Нет'
        line = f"{mbo}\t{audio['artist']}\t{audio['title']}\t{audio['source']}\t{audio['savers_count']}\t"
        if audio['post_owner_id'] and audio['post_id']:
            line += f"https://vk.com/wall{audio['post_owner_id']}_{audio['post_id']}"
        else:
            line += '-'
        line += '\n'
        header += line
    return header
