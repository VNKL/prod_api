from django.utils import timezone

from .models import Campaign, Ad, Playlist, Audio, Automate
from vk.ads.ads import VkAds
from ..users.models import User


def create_campaign(user, data):
    campaign = Campaign(owner=user, **data)
    campaign.save()
    return {'campaign_id': campaign.pk}


def delete_campaign(user, data):
    campaign = Campaign.objects.filter(owner=user, campaign_id=data['id']).first()
    if not campaign:
        return {'error': f'not found or no permissions to campaign with id {data["id"]}'}

    campaign.delete()
    return {'response': f"campaign with id {data['id']} was deleted"}


def create_automate(user, data):
    campaign = Campaign.objects.filter(owner=user, campaign_id=data['campaign_id']).first()
    if campaign:
        data.pop('campaign_id')
        automate = Automate(campaign=campaign, create_date=timezone.now(), **data)
        if data['start'] == 1:
            automate.status = 2
        automate.save()
        return {'automate_id': automate.pk}
    else:
        return {'error': f'Campaign with id {data["campaign_id"]} not found in user campaigns'}


def stop_automate(user, data):
    automate = Automate.objects.filter(campaign__owner=user, pk=data['id']).first()
    if not automate:
        return {'error': f'not found or no permissions to automate with id {data["id"]}'}

    automate.status = 0
    automate.finish_date = timezone.now()
    automate.save()

    campaign = Campaign.objects.filter(pk=automate.campaign.pk).first()
    if campaign:
        campaign.is_automate = False
        campaign.save()

    return {'response': f"stopping automate with id {data['id']}"}


def get_cabs_and_groups(username):
    user = User.objects.filter(username=username).first()
    if user:
        vk = VkAds(user.ads_token)
        cabs, groups = vk.get_cabs_and_groups()
        if cabs and groups:
            return {'cabinets': cabs, 'groups': groups}
        return {'error': 'error with get user cabinets and groups'}
    else:
        return {'error': 'error with get user'}


def get_retarget(username, cabinet_data):
    user = User.objects.filter(username=username).first()
    if user:
        cabinet = {'account_id': cabinet_data['cabinet_id'],
                   'client_id': cabinet_data['client_id'] if 'client_id' in cabinet_data.keys() else None}
        vk = VkAds(user.ads_token)
        return vk.get_retarget(cabinet)
    else:
        return {'error': 'error with get user'}


def update_campaign_stats(campaign):
    token = campaign.owner.ads_token
    if not token:
        return campaign

    ads = Ad.objects.filter(campaign=campaign)
    if not ads:
        return campaign

    vk = VkAds(token)
    camp_status, money_limit = vk.get_campaign_status(campaign.cabinet_id, campaign.campaign_id, campaign.client_id)
    campaign.status = int(camp_status) if camp_status else campaign.status
    ads_stat = vk.get_ads_stat(campaign.cabinet_id, campaign.campaign_id, campaign.client_id)

    if campaign.has_moderate_audios and not campaign.audios_is_moderated:
        _pars_post_audios_after_moderate(ads, ads_stat, campaign, vk)

    playlists_stat = vk.get_playlists_stat(campaign.fake_group_id)
    audios_stat = vk.get_audios_stat(_get_campaign_audios(ads))
    print(2222222, audios_stat)
    all_audio_stat = {'audios': audios_stat, 'playlists': playlists_stat}

    updated_ads, updated_playlists, updated_audios = [], [], []
    camp_spent, camp_reach, camp_listens, camp_saves, camp_clicks, camp_joins = [0], [0], [0], [0], [0], [0]
    for ad in ads:
        _process_ad(ad, ads_stat, all_audio_stat, camp_spent, camp_reach, camp_listens, camp_saves, camp_clicks, camp_joins,
                    updated_ads, updated_audios, updated_playlists)

    Ad.objects.bulk_update(updated_ads, batch_size=20, fields=['ad_name', 'status', 'approved', 'spent',
                                                               'reach', 'cpm', 'cpm_price', 'listens', 'cpl', 'lr',
                                                               'saves', 'cps', 'sr', 'clicks', 'cpc', 'cr',
                                                               'joins', 'cpj', 'jr'])
    Playlist.objects.bulk_update(updated_playlists, batch_size=40, fields=['listens', 'followers'])
    Audio.objects.bulk_update(updated_audios, batch_size=40, fields=['savers_count'])

    _process_campaign_stat(camp_listens, camp_reach, camp_saves, camp_spent, camp_clicks, camp_joins, campaign)

    return campaign, money_limit


def camp_stat_to_str(stat):
    cs = ['Остановлена', 'Запущена', 'Удалена']
    ad_s = ['Остановлено', 'Запущено', 'Удалено']
    ms = ['Не модерировалось', 'На модерации', 'Одобрено', 'Отклонено']

    header = 'Сегмент\tСсылка на объявление\tСсылка на пост\tСтатус\tМодерация\tПотрачено\tПоказы\tCPM\t' \
             'Прослушивания\tСтоимость прослушивания\tКонверсия в прослушивания\t' \
             'Добавления\tСтоимость добавления\tКонверсия в добавления\t' \
             'Переходы\tСтоимость перехода\tКонверсия в переходы\t' \
             'Подписки\tСтоимость подписки\tКонверсия в подписки\t' \
             'Размер аудитории\n'

    header += f"*кампания в целом*\t-\t-\t{cs[stat['status']]}\t-\t" \
              f"{stat['spent']}\t{stat['reach']}\t{stat['cpm']}\t" \
              f"{stat['listens']}\t{stat['cpl']}\t{round((stat['lr'] * 100), 3)} %\t" \
              f"{stat['saves']}\t{stat['cps']}\t{round((stat['sr'] * 100), 3)} %\t" \
              f"{stat['clicks']}\t{stat['cpc']}\t{round((stat['cr'] * 100), 3)} %\t" \
              f"{stat['joins']}\t{stat['cpj']}\t{round((stat['jr'] * 100), 3)} %\t" \
              f"{stat['audience_count']}\n"

    for ad in stat['ads']:
        header += f"{ad['ad_name']}\t" \
                  f"https://vk.com/ads?act=office&union_id={ad['ad_id']}\t" \
                  f"https://vk.com/wall-{ad['post_owner']}_{ad['post_id']}\t" \
                  f"{ad_s[ad['status']]}\t{ms[ad['approved']]}\t" \
                  f"{ad['spent']}\t{ad['reach']}\t{ad['cpm']}\t" \
                  f"{ad['listens']}\t{ad['cpl']}\t{round((ad['lr'] * 100), 3)} %\t" \
                  f"{ad['saves']}\t{ad['cps']}\t{round((ad['sr'] * 100), 3)} %\t" \
                  f"{ad['clicks']}\t{ad['cpc']}\t{round((ad['cr'] * 100), 3)} %\t" \
                  f"{ad['joins']}\t{ad['cpj']}\t{round((ad['jr'] * 100), 3)} %\t" \
                  f"{ad['audience_count']}\n"

    text = header.replace('.', ',')
    text = text.replace('vk,com', 'vk.com')
    return text


def camp_stat_to_filename(stat):
    if stat['update_date']:
        time = stat['update_date'].split('.')[0].replace('T', ' ').replace(':', '-')
        filename = f"{stat['campaign_name']} ({time}).csv"
    else:
        filename = f"{stat['campaign_name']}.csv"
    return filename


def _pars_post_audios_after_moderate(ads, ads_stat, campaign, vk):
    if ads_stat:
        posts_ids_for_get_audios = _get_posts_ids_for_get_audios_from_post(ads, ads_stat)
        if posts_ids_for_get_audios:
            posts = vk.get_posts_by_ids(posts_ids_for_get_audios)
            if posts:
                campaign.audios_is_moderated = True
                match_ads_and_audios(ads, posts)


def _process_campaign_stat(camp_listens, camp_reach, camp_saves, camp_spent, camp_clicks, camp_joins, campaign):
    campaign.spent = round(sum(camp_spent), 2) if sum(camp_spent) > campaign.spent else campaign.spent
    campaign.reach = sum(camp_reach) if sum(camp_reach) > campaign.reach else campaign.reach
    campaign.listens = sum(camp_listens) if sum(camp_listens) > campaign.listens else campaign.listens
    campaign.saves = sum(camp_saves) if sum(camp_saves) > campaign.saves else campaign.saves
    campaign.clicks = sum(camp_clicks) if sum(camp_clicks) > campaign.clicks else campaign.clicks
    campaign.joins = sum(camp_joins) if sum(camp_joins) > campaign.joins else campaign.joins
    campaign.cpm = round((campaign.spent / (campaign.reach / 1000)), 2) if campaign.reach else 0
    campaign.cpl = round((campaign.spent / campaign.listens), 2) if campaign.listens else 0
    campaign.cps = round((campaign.spent / campaign.saves), 2) if campaign.saves else 0
    campaign.cpc = round((campaign.spent / campaign.clicks), 2) if campaign.clicks else 0
    campaign.cpj = round((campaign.spent / campaign.joins), 2) if campaign.joins else 0
    campaign.lr = round((campaign.listens / campaign.reach), 4) if campaign.reach else 0
    campaign.sr = round((campaign.saves / campaign.reach), 4) if campaign.reach else 0
    campaign.cr = round((campaign.clicks / campaign.reach), 4) if campaign.reach else 0
    campaign.jr = round((campaign.joins / campaign.reach), 4) if campaign.reach else 0

    campaign.update_date = timezone.now()
    campaign.save()


def _process_ad(ad, ads_stat, all_audio_stat, camp_spent, camp_reach, camp_listens, camp_saves, camp_clicks, camp_joins,
                updated_ads, updated_audios, updated_playlists):
    ad_listens, ad_saves = [0], [0]

    playlist = Playlist.objects.filter(ad=ad).first()
    if playlist:
        _process_playlist_stat(all_audio_stat, camp_listens, camp_saves, ad_listens, ad_saves,
                               playlist, updated_playlists)

    audios = Audio.objects.filter(ad=ad)
    if audios:
        for audio in audios:
            _process_audio_stat(audio, all_audio_stat, camp_saves, updated_audios, ad_saves)

    _process_ad_stat(ad, ads_stat, camp_spent, camp_reach, camp_clicks, camp_joins, ad_listens, ad_saves)
    updated_ads.append(ad)


def _process_ad_stat(ad, ads_stat, camp_spent, camp_reach, camp_clicks, camp_joins, ad_listens, ad_saves):
    if ads_stat and ad.ad_id in ads_stat.keys():
        ad_stat = ads_stat[ad.ad_id]
        ad.ad_name = ad_stat['name']
        ad.status = ad_stat['status']
        ad.approved = ad_stat['approved']
        ad.cpm_price = ad_stat['cpm'] if 'cpm' in ad_stat.keys() else ad.cpm_price
        ad.spent = ad_stat['spent'] if 'spent' in ad_stat.keys() else 0
        ad.reach = ad_stat['reach'] if 'reach' in ad_stat.keys() else 0
        ad.clicks = ad_stat['clicks'] if 'clicks' in ad_stat.keys() else 0
        ad.joins = ad_stat['joins'] if 'joins' in ad_stat.keys() else 0
        camp_spent.append(ad_stat['spent'] if 'spent' in ad_stat.keys() else 0)
        camp_reach.append(ad_stat['reach'] if 'reach' in ad_stat.keys() else 0)
        camp_clicks.append(ad_stat['clicks'] if 'clicks' in ad_stat.keys() else 0)
        camp_joins.append(ad_stat['joins'] if 'joins' in ad_stat.keys() else 0)

    ad.cpm = round((ad.spent / (ad.reach / 1000)), 2) if ad.reach else 0
    ad.listens = sum(ad_listens) if sum(ad_listens) > ad.listens else ad.listens
    ad.cpl = round((ad.spent / ad.listens), 2) if ad.listens else 0
    ad.lr = round((ad.listens / ad.reach), 4) if ad.reach else 0
    ad.saves = sum(ad_saves) if sum(ad_saves) > ad.saves else ad.saves
    ad.cps = round((ad.spent / ad.saves), 2) if ad.saves else 0
    ad.sr = round((ad.saves / ad.reach), 4) if ad.reach else 0
    ad.cpc = round((ad.spent / ad.clicks), 2) if ad.clicks else 0
    ad.cr = round((ad.clicks / ad.reach), 4) if ad.reach else 0
    ad.cpj = round((ad.spent / ad.clicks), 2) if ad.clicks else 0
    ad.jr = round((ad.joins / ad.reach), 4) if ad.reach else 0


def _process_audio_stat(audio, all_audio_stat, camp_saves, updated_audios, ad_saves):
    audio_full_id = f"{audio.owner_id}_{audio.audio_id}"
    au_stat = [x for x in all_audio_stat['audios'] if f"{x['owner_id']}_{x['id']}" == audio_full_id]
    if au_stat and 'savers_count' in au_stat[0]:
        audio.savers_count = au_stat[0]['savers_count'] if au_stat[0]['savers_count'] else 0
        ad_saves.append(au_stat[0]['savers_count'] if au_stat[0]['savers_count'] else 0)
        camp_saves.append(au_stat[0]['savers_count'] if au_stat[0]['savers_count'] else 0)
        updated_audios.append(audio)


def _process_playlist_stat(all_audio_stat, camp_listens, camp_saves, ad_listens, ad_saves,
                           playlist, updated_playlists):
    pl_stat = [x for x in all_audio_stat['playlists'] if x['id'] == playlist.playlist_id]
    if pl_stat:
        playlist.listens = pl_stat[0]['plays'] if pl_stat[0]['plays'] else 0
        playlist.followers = pl_stat[0]['followers'] if pl_stat[0]['followers'] else 0
        ad_listens.append(pl_stat[0]['plays'] if pl_stat[0]['plays'] else 0)
        ad_saves.append(pl_stat[0]['followers'] if pl_stat[0]['followers'] else 0)
        camp_listens.append(pl_stat[0]['plays'] if pl_stat[0]['plays'] else 0)
        camp_saves.append(pl_stat[0]['followers'] if pl_stat[0]['followers'] else 0)
        updated_playlists.append(playlist)


def _get_posts_ids_for_get_audios_from_post(ads, ads_stat):
    post_ids = []
    for ad in ads:
        audios = Audio.objects.filter(ad=ad)
        post_audios = [x for x in audios if not x.in_playlist and not x.audio_id] if audios else None
        if post_audios and ads_stat[ad.ad_id]['approved'] == 2 and ad.approved == 1:
            post_ids.append(f'-{ad.post_owner}_{ad.post_id}')
    return post_ids


def match_ads_and_audios(ads, posts):
    matched_audio_objs = []
    for ad in ads:
        for post in posts:
            if f"{post['owner_id']}_{post['id']}" == f"-{ad.post_owner}_{ad.post_id}":
                post_audios = [x['audio'] for x in post['attachments'] if x['type'] == 'audio']
                post_audio_objs = Audio.objects.filter(ad=ad)
                for n, audio_obj in enumerate(post_audio_objs):
                    audio_obj.owner_id = post_audios[n]['owner_id']
                    audio_obj.audio_id = post_audios[n]['id']
                    matched_audio_objs.append(audio_obj)

    Audio.objects.bulk_update(matched_audio_objs, fields=['owner_id', 'audio_id'], batch_size=40)


def _get_campaign_audios(ads):
    all_audios = []
    for ad in ads:
        audios = Audio.objects.filter(ad=ad)
        if audios:
            refact_audios = [{'owner_id': x.owner_id, 'id': x.audio_id} for x in audios if x.owner_id and x.audio_id]
            all_audios.extend(refact_audios)
    print(11111, all_audios)
    return all_audios
