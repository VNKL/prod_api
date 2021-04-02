import bs4
import datetime


def convert_service_id(service):
    services_ids = {'am': 1, 'vk': 2, 'ok': 3, 'dz': 4, 'it': 5, 'ms': 6, 'sz': 7, 'yt': 8, 'ym': 9, 'zv': 10, 'sp': 11}
    if service in services_ids.keys():
        return services_ids[service]


def compile_mooscle_urls(service_id, date):
    main_url = f'https://mooscle.com/charts/?date={date}&type=song&tab={service_id}'
    scroll_url = f'https://mooscle.com/wp/wp-admin/admin-ajax.php?date={date}&type=song&tab={service_id}&' \
                 f'date={date}&type=song&tab={service_id}&action=chart_items_more&customer_id={service_id}'
    return [main_url, scroll_url]


def pars_mooscle_chart_batch(track_list):
    parsed_tracks = []
    if track_list:
        tracks = track_list.find_all(class_='chart-list-item')
        if tracks:
            for track in tracks:
                track_obj = {
                    'artist': _check_mooslce_tag(track.find(class_='inline').get_text()),
                    'title': _check_mooslce_tag(track.find(class_='title').get_text()),
                    'position': _check_mooslce_tag(track.find(class_='position-wrap').get_text()),
                    'cover': _check_mooslce_tag(track.find('img')['src']),
                    'distributor': _check_mooslce_tag(track.find(class_='label label-default main-v'))
                }
                parsed_tracks.append(track_obj)
    return parsed_tracks


def _check_mooslce_tag(string):
    if isinstance(string, bs4.element.Tag):
        if string['title'] == '':
            string = string.get_text()
        else:
            string = string['title']

    if string and len(string) > 1 and string[-1] == ' ':
        string = string[:-1]

    if string == '':
        return None

    if string:
        return string


def dates_period_to_list(date_from, date_to):
    start = datetime.datetime.strptime(f'{date_from}', '%d.%m.%Y')
    end = datetime.datetime.strptime(f'{date_to}', '%d.%m.%Y')
    date_generated = [start + datetime.timedelta(days=x) for x in range(0, (end - start).days + 1)]

    date_list = []
    for i in date_generated:
        date = str(i.strftime("%d.%m.%Y"))
        date_list.append(date)

    return date_list