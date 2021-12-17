import json


def code_for_get_cabs_and_groups():
    code = 'var cabinets = API.ads.getAccounts(); ' \
           'var groups = API.groups.get({"filter": "admin", "count": 1000, "extended": 1}); ' \
           'var result = {"cabinets": cabinets, "groups": groups}; ' \
           'return result;'
    return code


def code_for_get_group_audios(group_id):
    code = 'var audios = API.audio.get({owner_id: -' + str(group_id) + ', count: 2000}); ' \
           'var playlists = API.audio.getPlaylists({owner_id: -' + str(group_id) + ', count: 200}); ' \
           'var result = {audios: audios.items, playlists: playlists.items}; ' \
           'return result;'
    return code


def code_for_get_audios_stat(audios):
    code = 'return ['
    for audio in audios:
        code += 'API.likes.getList({type: "audio", ' \
                                   'owner_id: ' + str(audio['owner_id']) + ', ' \
                                   'item_id: ' + str(audio['id']) + '}).count, '
    code = code[:-2]
    code += '];'
    return code


def code_for_create_fake_group(group_name, acc_user_id):
    code = 'var group_id = API.groups.create({title: "' + group_name + '", type: "public", ' \
                                             'public_category: 1002, subtype: 3}).id; ' \
           'API.groups.editManager({group_id: group_id, is_contact: 0, user_id: ' + str(acc_user_id) + '}); ' \
           'return group_id; '
    return code


def code_for_add_audios_in_group(audios, group_id):
    code = 'return ['
    for audio in audios:
        code += 'API.audio.add({owner_id: ' + str(audio['owner_id']) + ', ' \
                               'audio_id: ' + str(audio['id']) + ', ' \
                               'group_id: ' + str(group_id) + '}), '
    code = code[:-2]
    code += '];'
    return code


def get_ads_stat_summary(ads, stat):
    bad_fields = ['ad_format', 'ad_platform', 'age_restriction', 'all_limit', 'category1_id', 'category2_id',
                  'conversion_event_id', 'conversion_pixel_id', 'cost_type', 'create_time', 'day_limit',
                  'events_retargeting_groups', 'goal_type', 'impressions_limit', 'impressions_limit_period',
                  'start_time', 'stop_time', 'update_time']

    summary_stat = {int(ad['id']): ad for ad in ads if 'cpm' in ad.keys()}
    for v in summary_stat.values():
        v['cpm'] = round((int(v['cpm']) / 100), 2)
        v['id'] = int(v['id'])
        v['approved'] = int(v['approved'])
        v['status'] = int(v['status'])
        v['spent'] = 0
        v['reach'] = 0
        for field in bad_fields:
            v.pop(field, None)

    if not stat:
        return summary_stat

    for ad in stat:
        if ad['stats']:
            summary_stat[ad['id']].update(
                {'spent': float(ad['stats'][0]['spent']) if 'spent' in ad['stats'][0].keys() else 0,
                 'reach': int(ad['stats'][0]['impressions']) if 'impressions' in ad['stats'][0].keys() else 0,
                 'clicks': int(ad['stats'][0]['clicks']) if 'clicks' in ad['stats'][0].keys() else 0,
                 'joins': int(ad['stats'][0]['join_rate']) if 'join_rate' in ad['stats'][0].keys() else 0}
            )
    return summary_stat


def get_data_dicts_for_update_ads(ad_ids, money_limit=None, start=False, stop=False, cpm_list=None):
    datas = []
    for n, ad_id in enumerate(ad_ids):
        data = {'ad_id': ad_id}
        if isinstance(money_limit, int):
            data['all_limit'] = money_limit
        if start:
            data['status'] = 1
        elif stop:
            data['status'] = 0
        if cpm_list:
            data['cpm'] = cpm_list[n]
        if len(data) > 1:
            datas.append(data)
    return datas


def get_data_for_update_campaign(campaign_id, money_limit=None, start=False, stop=False):
    data = {'campaign_id': campaign_id}
    if isinstance(money_limit, int):
        data['all_limit'] = money_limit
    if start:
        data['status'] = 1
    elif stop:
        data['status'] = 0
    return data


def simplify_vk_objs(items, obj_type=None):
    if not items:
        return items
    elif not isinstance(items, list):
        items = [items]

    if obj_type == 'audio':
        bad_fields = ['ads', 'album', 'date', 'duration', 'is_explicit', 'is_hq', 'is_licensed', 'main_artists',
                      'short_videos_allowed', 'stories_allowed', 'stories_cover_allowed', 'track_code', 'url',
                      'no_search']
    elif obj_type == 'playlist':
        bad_fields = ['album_type', 'count', 'create_time', 'description', 'genres', 'is_following',
                      'thumbs', 'type', 'update_time', 'photo']
    else:
        bad_fields = []

    processed_items = []
    for item in items:
        simple_item = item.copy()
        if obj_type == 'audio':
            simple_item['domains'] = _pars_artist_domains_from_audio(item)
        for field in bad_fields:
            simple_item.pop(field, None)
        processed_items.append(simple_item)

    return processed_items


def _pars_artist_domains_from_audio(audio):
    domains = []
    for artists_type in ['main_artists', 'featured_artists']:
        if artists_type in audio.keys() and audio[artists_type]:
            for artist in audio[artists_type]:
                if 'domain' in artist.keys() and artist['domain']:
                    domains.append(f"https://vk.com/artist/{artist['domain']}")
    return domains


def pars_post_id_from_post_url(post_url):
    if 'wall' not in post_url:
        if '_' in post_url:
            owner_id, post_id = post_url.split('-')
            try:
                owner_id, post_url = int(owner_id), int(post_id)
                return f'{owner_id}_{post_id}'
            except TypeError:
                return None
    else:
        return post_url.split('wall')[-1]


def pars_attach_items_from_post(post, attach_type):
    items_strs = []
    for attach in post['attachments']:
        if attach['type'] == attach_type:
            item = attach[attach_type]
            item_str = f"{attach_type}{item['owner_id']}_{item['id']}"
            items_strs.append(item_str)
    return items_strs


def pars_playlists_from_post(post):
    for attach in post['attachments']:
        if attach['type'] == 'link' and 'audio_playlist' in attach['link']['url']:
            pl_url = attach['link']['url']
            title = attach['link']['title']
            owner_id, pl_id = pl_url.split('audio_playlist')[1].split('&')[0].split('_')
            access_hash = None
            if 'access_hash' in pl_url:
                access_hash = pl_url.split('access_hash=')[1].split('&')[0]
            return {'title': title, 'owner_id': int(owner_id), 'playlist_id': int(pl_id), 'access_key': access_hash}


def get_cover_from_obj(obj):
    if 'photo_1200' in obj.keys():
        return obj['photo_1200']
    elif 'photo_600' in obj.keys():
        return obj['photo_600']
    elif 'photo_300' in obj.keys():
        return obj['photo_300']
    elif 'photo_270' in obj.keys():
        return obj['photo_270']


def get_artist_and_title_from_reference(reference):
    if reference['audios']:
        return reference['audios'][0]['artist'], reference['audios'][0]['title']
    elif reference['playlist']:
        main_audio = None
        for audio in reference['playlist']['audios']:
            if not main_audio or len(audio['domains']) < len(main_audio['domains']):
                main_audio = audio
        return main_audio['artist'], reference['playlist']['title']
    else:
        return 'Новинки Музыки', 'Без названия'


def get_attachments_for_post(replica_obj):
    attachments = ''
    for attach in replica_obj['attachments']:
        for attach_strs in attach.values():
            for attach_str in attach_strs:
                attachments += f'{attach_str},'
    if replica_obj['audios']:
        for audio in replica_obj['audios']:
            audio_str = f"audio{audio['owner_id']}_{audio['id']}"
            attachments += f'{audio_str},'
    if replica_obj['playlist']:
        playlist_str = f"audio_playlist{replica_obj['playlist']['owner_id']}_{replica_obj['playlist']['playlist_id']}"
        attachments += f'{playlist_str},'
    if attachments[-1] == ',':
        attachments = attachments[:-1]
    return attachments


def get_group_id_from_url(group_str):
    if 'https://vk.com/public' in group_str:
        return group_str.split('https://vk.com/public')[1]
    elif 'https://vk.com/' in group_str:
        return group_str.split('https://vk.com/')[1]


def data_for_create_ads(ad_name, campaign_id, post_url, sex=None, music=False, boom=None,
                        musician_formula=None, groups_formula=None, retarget_id=None,
                        age_from=0, age_to=0, age_disclaimer='0+', retarget_exclude_id=None,
                        retarget_save_seen_id=None, retarget_save_positive_id=None, retarget_save_negative_id=None):
    # Перевод параметров функции в параметры для настроек
    sex = _sex_str_to_int(sex)
    age_disclaimer = age_disclaimer if isinstance(age_disclaimer, int) else _age_disclaimer_str_to_int(age_disclaimer)
    age_from = _age_from_by_int_age_disclaimer(age_disclaimer, age_from)

    # Сохранение событий в ретаргет
    retarget_save = {}
    if retarget_save_seen_id:
        retarget_save[retarget_save_seen_id] = [1]
    if retarget_save_positive_id:
        retarget_save[retarget_save_positive_id] = [2, 3, 4, 20, 21]
    if retarget_save_negative_id:
        retarget_save[retarget_save_negative_id] = [5, 6]

    data_dict = {
        'campaign_id': campaign_id,                 # Айди кампании
        'ad_format': 9,                             # Формат объявления, 9 - посты
        'autobidding': 0,                           # Автоуправление ценой
        'cost_type': 1,                             # Способ оплаты, 1 - СРМ
        'cpm': 30.,                                 # CPM
        'impressions_limit': 1,                     # Показы на одного человека
        'ad_platform': 'mobile',                    # Площадки показа
        'all_limit': 100,                           # Лимит по бюджету
        'category1_id': 51,                         # Тематика объявления, 51 - музыка
        'age_restriction': age_disclaimer,          # Возрастной дисклеймер, 1 - 0+, 2 - 6+, 3 - 12+, 4 - 16+, 5 - 18+
        'status': 1,                                # Статус объявления, 1 - запущено
        'name': ad_name,                            # Название объявления
        'link_url': post_url,                       # Ссылка на дарк-пост
        'country': 0,                               # Страна, 0 - не задана
        'user_devices': 1001,                       # Устройства, 1001 - смартфоны
        'sex': sex,                                 # Пол, 0 - любой, 1 - женский, 2 - мужской
        'age_from': age_from,                       # Возраст от, 0 - не задано
        'age_to': age_to                            # Возраст до, 0 - не задано
    }
    if music:
        data_dict.update({'interest_categories': 10010})  # Категории интересов, 10010 - музыка
    if musician_formula:
        data_dict.update({'music_artists_formula': musician_formula})
    if groups_formula:
        data_dict.update({'groups_active_formula': groups_formula})
    if retarget_id:
        data_dict.update({'retargeting_groups': retarget_id})
    if boom:
        data_dict.update({'apps': 4705861})
    if 'Пустой сегмент' in ad_name:
        data_dict.update({'status': 0})
    if retarget_exclude_id:
        data_dict.update({'retargeting_groups_not': retarget_exclude_id})
    if retarget_save:
        data_dict.update({'events_retargeting_groups': retarget_save})

    return json.dumps([data_dict])


def _sex_str_to_int(sex):
    if sex == 'male':
        return 2
    elif sex == 'female':
        return 1
    else:
        return 0


def _age_disclaimer_str_to_int(age_disclaimer):
    if not age_disclaimer:
        return 1
    elif age_disclaimer == '0+':
        return 1
    elif age_disclaimer == '6+':
        return 2
    elif age_disclaimer == '12+':
        return 3
    elif age_disclaimer == '16+':
        return 4
    elif age_disclaimer == '18+':
        return 5
    else:
        return 1


def _age_from_by_int_age_disclaimer(age_disclaimer, age_from):
    if age_disclaimer == 2 and age_from < 6:
        return 14
    elif age_disclaimer == 3 and age_from < 12:
        return 14
    elif age_disclaimer == 4 and age_from < 16:
        return 16
    elif age_disclaimer == 5 and age_from < 18:
        return 18
    else:
        return age_from
