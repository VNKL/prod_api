import copy
import json
import traceback

from time import sleep
from random import uniform

from django.core.management.base import BaseCommand
from django import db

from api.ads.models import Campaign, Ad, Audio, Playlist
from vk.ads.ads import VkAds
from vk.ads.utils import get_artist_and_title_from_reference
from vk.related.parser import VkRelatedParser
from api.settings import FEAT_SPLIT_SIMPOLS


class Command(BaseCommand):
    help = 'start new campaign'

    def add_arguments(self, parser):
        parser.add_argument('-campaign_id', action='store', dest='campaign_id', type=int)

    def handle(self, *args, **options):
        if 'campaign_id' not in options.keys():
            print('campaign_id is required to start_campaign command')
        else:
            start_campaign(options['campaign_id'])


def start_campaign(campaign_id):

    campaign = Campaign.objects.filter(pk=campaign_id).first()
    if not campaign:
        print(f'no campaign with id {campaign_id}')
    else:
        try:
            _start_campaign(campaign)
            db.connections.close_all()
        except Exception:
            campaign.errors = traceback.format_exc()
            campaign.status = 3
            campaign.save()
            db.connections.close_all()


def _start_campaign(campaign):

    campaign = _wait_queue(campaign)
    if not campaign:
        return

    ads, errors, reference, campaign_id, fake_group_id = [], [], None, None, None,

    vk = _get_vk(campaign, errors)
    if vk:
        reference = _pars_reference(vk, campaign, errors)

    if reference:
        campaign_id = _create_campaign(reference, vk, campaign, errors)

    if campaign_id:
        _save_cabinet_name(vk, campaign)
        fake_group_id = _create_fake_group(vk, campaign, errors)

    if fake_group_id:
        campaign.fake_group_id = fake_group_id
        campaign.save()
        ads.extend(_create_ads(campaign, reference, vk))

    if not ads:
        errors.append('No ads for received campaign settings')
        campaign.errors = json.dumps(errors)
        campaign.status = 3

    else:
        campaign.status = 1
        campaign.audience_count = sum([x.audience_count for x in ads])

    campaign.save()
    db.connections.close_all()


def _wait_queue(campaign):
    earlier_campaigns = Campaign.objects.filter(owner=campaign.owner, status__in=[4, 5]).exclude(pk=campaign.pk)
    if earlier_campaigns:
        earlier_running = [True for _ in earlier_campaigns]
        while any(earlier_running):
            sleep(uniform(5, 15))
            for n, earlier_campaign in enumerate(earlier_campaigns):
                try:
                    earlier_campaign.refresh_from_db()
                    if earlier_campaign.status in [0, 1, 2, 3]:
                        earlier_running[n] = False
                except Campaign.DoesNotExist:
                    earlier_running[n] = False
                db.connections.close_all()

    campaign = Campaign.objects.filter(pk=campaign.pk).first()
    if campaign:
        campaign.status = 5
        campaign.save()
        db.connections.close_all()
        return campaign
    else:
        db.connections.close_all()
        return False


def _get_vk(campaign, errors):
    token = campaign.owner.ads_token
    if token:
        return VkAds(token)
    else:
        errors.append('Campaign owner have no ads_token')


def _pars_reference(vk, campaign, errors):
    reference = vk.pars_reference_post(post_url=campaign.reference_url)
    if reference:
        campaign.reference = json.dumps(reference)
        if reference['cover_url']:
            campaign.cover_url = reference['cover_url']
        return reference
    else:
        errors.append(f'Error with parsing reference post from url {campaign.reference_url}')


def _pars_artist_and_title(reference, campaign, errors):
    artist, title = get_artist_and_title_from_reference(reference=reference)
    if artist and title:
        campaign.artist = artist
        campaign.title = title
        return artist, title
    else:
        errors.append(f'Error with parsing artist and title from reference post in url {campaign.reference_url}')
        return None, None


def _create_campaign(reference, vk, campaign, errors):

    artist, title = _pars_artist_and_title(reference, campaign, errors)
    if artist and title:
        camp_name = f'{artist} - {title}'
        camp_id = vk.create_campaign(cabinet_id=campaign.cabinet_id, client_id=campaign.client_id,
                                     campaign_name=camp_name, money_limit=campaign.money_limit)
        if camp_id:
            campaign.campaign_id = camp_id
            campaign.campaign_name = camp_name
            campaign.save()
            db.connections.close_all()
            return camp_id
        else:
            db.connections.close_all()
            err_msg = f'Error with create campaign with name "{camp_name}" in cabinet {campaign.cabinet_id}'
            err_msg = err_msg + f' and client {campaign.client_id}' if campaign.client_id else ''
            errors.append(err_msg)


def _create_fake_group(vk, campaign, errors):
    fake_group_id = vk.create_fake_group(group_name=campaign.artist)
    if fake_group_id:
        campaign.fake_group_id = fake_group_id
        return fake_group_id
    else:
        errors.append(f'Error with create fake group with name "{campaign.artist}"')


def _create_ads(campaign, reference, vk):
    ads = []
    save_retarget_dict = _get_save_retarget_ids(campaign, vk)
    ads.extend(_create_ads_for_groups(reference, vk, campaign, save_retarget_dict))
    ads.extend(_create_ads_for_retarget(reference, vk, campaign, save_retarget_dict))
    ads.extend(_create_ads_for_musicians(reference, vk, campaign, save_retarget_dict))
    ads.extend(_create_empty_ads(reference, vk, campaign, save_retarget_dict))
    return ads


def _get_save_retarget_ids(campaign, vk):
    exclude = campaign.retarget_exclude
    save_seen_id = campaign.retarget_save_seen
    save_positive_id = campaign.retarget_save_positive
    save_negative_id = campaign.retarget_save_negative

    if exclude or save_seen_id or save_positive_id or save_negative_id:
        cab_retarget = vk.get_retarget({'account_id': campaign.cabinet_id, 'client_id': campaign.client_id})
        cab_retarget = {x['name']: x['id'] for x in cab_retarget}

        if exclude:
            if '\n' in exclude:
                exclude_list = exclude.split('\n')
            else:
                exclude_list = [exclude]
            exclude_ids_list = [str(v) for k, v in cab_retarget.items() if k in exclude_list]
            if exclude_ids_list:
                exclude = ','.join(exclude_ids_list)
            else:
                exclude = None

        if save_seen_id:
            save_seen_id = cab_retarget[save_seen_id] if save_seen_id in cab_retarget.keys() else None

        if save_positive_id:
            save_positive_id = cab_retarget[save_positive_id] if save_positive_id in cab_retarget.keys() else None

        if save_negative_id:
            save_negative_id = cab_retarget[save_negative_id] if save_negative_id in cab_retarget.keys() else None

        return {
            'exclude': exclude,
            'save_seen_id': save_seen_id,
            'save_positive_id': save_positive_id,
            'save_negative_id': save_negative_id
        }

    return {'exclude': None, 'save_seen_id': None, 'save_positive_id': None, 'save_negative_id': None}


def _create_ads_for_musicians(reference_orig, vk, campaign, save_retarget_dict):
    ads = []
    musicians = _get_musicians(campaign)
    for musician in musicians:
        try:
            formula = vk.get_music_artist_formula(musician)
            if formula:
                reference = copy.deepcopy(reference_orig)
                post_replica = vk.create_post_replica(reference, campaign.group_id, campaign.fake_group_id)
                if post_replica and 'post_url' in post_replica.keys():
                    ad_name = f'{musician} / слушатели'
                    ad_id = vk.create_ad(cabinet_id=campaign.cabinet_id, campaign_id=campaign.campaign_id,
                                         ad_name=ad_name, post_url=post_replica['post_url'],
                                         sex=campaign.sex, music=campaign.music, boom=campaign.boom,
                                         age_from=campaign.age_from, age_to=campaign.age_to,
                                         age_disclaimer=campaign.age_disclaimer, musician_formula=formula,
                                         retarget_exclude_id=save_retarget_dict['exclude'],
                                         retarget_save_seen_id=save_retarget_dict['save_seen_id'],
                                         retarget_save_positive_id=save_retarget_dict['save_positive_id'],
                                         retarget_save_negative_id=save_retarget_dict['save_negative_id'])
                    if ad_id:
                        sleep(uniform(1, 4))
                        audience_count = vk.get_segment_size(cabinet_id=campaign.cabinet_id, client_id=campaign.client_id,
                                                             ad_id=ad_id, post_url=post_replica['post_url'])
                        ad = _save_ad(campaign, ad_id, ad_name, post_replica, audience_count)
                        ads.append(ad)
        except Exception:
            continue

    return ads


def _create_ads_for_groups(reference_orig, vk, campaign, save_retarget_dict):
    ads = []
    groups = _get_groups(campaign)
    for group in groups:
        try:
            name, formula = vk.get_groups_names_and_formula(group)
            if name and formula:
                reference = copy.deepcopy(reference_orig)
                post_replica = vk.create_post_replica(reference, campaign.group_id, campaign.fake_group_id)
                if post_replica and 'post_url' in post_replica.keys():
                    ad_name = f'{name} / актив'
                    ad_id = vk.create_ad(cabinet_id=campaign.cabinet_id, campaign_id=campaign.campaign_id,
                                         ad_name=ad_name, post_url=post_replica['post_url'],
                                         sex=campaign.sex, music=campaign.music, boom=campaign.boom,
                                         age_from=campaign.age_from, age_to=campaign.age_to,
                                         age_disclaimer=campaign.age_disclaimer, groups_formula=formula,
                                         retarget_exclude_id=save_retarget_dict['exclude'],
                                         retarget_save_seen_id=save_retarget_dict['save_seen_id'],
                                         retarget_save_positive_id=save_retarget_dict['save_positive_id'],
                                         retarget_save_negative_id=save_retarget_dict['save_negative_id'])
                    if ad_id:
                        sleep(uniform(1, 4))
                        audience_count = vk.get_segment_size(cabinet_id=campaign.cabinet_id, client_id=campaign.client_id,
                                                             ad_id=ad_id, post_url=post_replica['post_url'])
                        ad = _save_ad(campaign, ad_id, ad_name, post_replica, audience_count)
                        ads.append(ad)
        except Exception:
            continue

    return ads


def _create_ads_for_retarget(reference_orig, vk, campaign, save_retarget_dict):
    ads = []
    retarget_names, cab_retarget = _get_retarget_names(vk, campaign)
    if not cab_retarget:
        return ads

    for retarget_name in retarget_names:
        try:
            retargets = [x for x in cab_retarget if x['name'] == retarget_name]
            for retarget in retargets:
                reference = copy.deepcopy(reference_orig)
                post_replica = vk.create_post_replica(reference, campaign.group_id, campaign.fake_group_id)
                if post_replica and 'post_url' in post_replica.keys():
                    ad_name = f'{retarget_name} / ретаргетинг'
                    ad_id = vk.create_ad(cabinet_id=campaign.cabinet_id, campaign_id=campaign.campaign_id,
                                         ad_name=ad_name, post_url=post_replica['post_url'],
                                         sex=campaign.sex, music=campaign.music, boom=campaign.boom,
                                         age_from=campaign.age_from, age_to=campaign.age_to,
                                         age_disclaimer=campaign.age_disclaimer, retarget_id=retarget['id'],
                                         retarget_exclude_id=save_retarget_dict['exclude'],
                                         retarget_save_seen_id=save_retarget_dict['save_seen_id'],
                                         retarget_save_positive_id=save_retarget_dict['save_positive_id'],
                                         retarget_save_negative_id=save_retarget_dict['save_negative_id'])
                    if ad_id:
                        sleep(uniform(1, 4))
                        audience_count = vk.get_segment_size(cabinet_id=campaign.cabinet_id, client_id=campaign.client_id,
                                                             ad_id=ad_id, post_url=post_replica['post_url'])
                        ad = _save_ad(campaign, ad_id, ad_name, post_replica, audience_count)
                        ads.append(ad)
        except Exception:
            continue

    return ads


def _create_empty_ads(reference_orig, vk, campaign, save_retarget_dict):
    ads = []
    names = [f'Пустой сегмент {i + 1}' for i in range(campaign.empty_ads)]
    for name in names:
        try:
            reference = copy.deepcopy(reference_orig)
            post_replica = vk.create_post_replica(reference, campaign.group_id, campaign.fake_group_id)
            if post_replica and 'post_url' in post_replica.keys():
                ad_id = vk.create_ad(cabinet_id=campaign.cabinet_id, campaign_id=campaign.campaign_id,
                                     ad_name=name, post_url=post_replica['post_url'],
                                     sex=campaign.sex, music=campaign.music, boom=campaign.boom,
                                     age_from=campaign.age_from, age_to=campaign.age_to,
                                     age_disclaimer=campaign.age_disclaimer,
                                     retarget_exclude_id=save_retarget_dict['exclude'],
                                     retarget_save_seen_id=save_retarget_dict['save_seen_id'],
                                     retarget_save_positive_id=save_retarget_dict['save_positive_id'],
                                     retarget_save_negative_id=save_retarget_dict['save_negative_id'])
                if ad_id:
                    sleep(uniform(1, 4))
                    audience_count = vk.get_segment_size(cabinet_id=campaign.cabinet_id, client_id=campaign.client_id,
                                                         ad_id=ad_id, post_url=post_replica['post_url'])
                    ad = _save_ad(campaign, ad_id, name, post_replica, audience_count)
                    ads.append(ad)
        except Exception:
            continue

    return ads


def _get_musicians(campaign):
    all_musicians = []

    artist = campaign.artist
    check_feat = [True if x in artist else False for x in FEAT_SPLIT_SIMPOLS]
    if not any(check_feat):
        all_musicians.append(artist)
    else:
        feat_musicians_variants = []
        for symbols in FEAT_SPLIT_SIMPOLS:
            if symbols in artist:
                feat_artists = artist.split(symbols)
                feat_musicians_variants.extend(feat_artists)
                feat_musicians_variants.append(', '.join(feat_artists))
        all_musicians.extend(feat_musicians_variants)

    musicians = campaign.musicians
    if musicians:
        if '\n' in musicians:
            all_musicians.extend(musicians.split('\n'))
        else:
            all_musicians.append(musicians)

    all_musicians.extend(_get_related(campaign))

    all_musicians = list(set(all_musicians))

    return all_musicians


def _get_related(campaign):
    if not campaign.related:
        return []

    reference = json.loads(campaign.reference)
    artist_urls = []
    if 'audios' in reference.keys() and reference['audios']:
        artist_urls.extend(_get_domains_from_reference_audio(reference['audios']))
    if 'playlist' in reference.keys() and isinstance(reference['playlist'], dict):
        if 'audios' in reference['playlist'].keys() and reference['playlist']['audios']:
            artist_urls.extend(_get_domains_from_reference_audio(reference['playlist']['audios']))

    related, vk = [], VkRelatedParser()
    for url in artist_urls:
        rels = vk.get_related_artists(artist_url=url, listens_min=25000, listens_max=75000, max_recurse=1)
        if rels:
            related.append(rels)

    names = []
    for item in related:
        if item['related']:
            for artist in item['related']:
                names.append(artist['name'])

    return names


def _get_domains_from_reference_audio(audios):
    artist_urls = []
    for audio in audios:
        if 'domains' in audio.keys() and audio['domains']:
            artist_urls.extend(audio['domains'])
    return artist_urls


def _get_groups(campaign):
    groups = []
    groups_str = campaign.groups
    if groups_str:
        if '\n' in groups_str:
            groups.extend(groups_str.split('\n'))
        else:
            groups.append(groups_str)
    return groups


def _get_retarget_names(vk, campaign):
    names, cab_retarget = [], []

    retarget = campaign.retarget
    if retarget:
        if '\n' in retarget:
            names.extend(retarget.split('\n'))
        else:
            names.append(retarget)
    if names:
        cab_retarget = vk.get_retarget({'account_id': campaign.cabinet_id, 'client_id': campaign.client_id})

    return names, cab_retarget


def _save_ad(campaign, ad_id, ad_name, post_replica, audience_count):
    status = 0 if 'Пустой сегмент' in ad_name else 1
    ad = Ad(campaign=campaign, ad_id=ad_id, ad_name=ad_name, status=status,
            post_owner=post_replica['owner_id'], post_id=post_replica['post_id'],
            audience_count=audience_count if audience_count else 0)
    ad.save()

    audios_objs = []

    if 'playlist' in post_replica.keys() and post_replica['playlist']:
        playlist = Playlist(ad=ad,
                            owner_id=post_replica['playlist']['owner_id'],
                            playlist_id=post_replica['playlist']['playlist_id'],
                            access_key=post_replica['playlist']['access_key'],
                            title=post_replica['playlist']['title'])
        playlist.save()
        for audio in post_replica['playlist']['audios']:
            audio = Audio(ad=ad, owner_id=audio['owner_id'], audio_id=audio['audio_id'],
                          artist=audio['artist'], title=audio['title'], in_playlist=True)
            audios_objs.append(audio)

    if 'audios' in post_replica.keys() and post_replica['audios']:
        for audio in post_replica['audios']:
            if 'in_playlist' in audio.keys() and audio['in_playlist']:
                audio = Audio(ad=ad, owner_id=audio['owner_id'], audio_id=audio['audio_id'],
                              artist=audio['artist'], title=audio['title'], in_playlist=True)
            else:
                audio = Audio(ad=ad, artist=audio['artist'], title=audio['title'], in_playlist=False)
                campaign.has_moderate_audios = True
            audios_objs.append(audio)

    if audios_objs:
        Audio.objects.bulk_create(audios_objs)

    db.connections.close_all()
    return ad


def _save_cabinet_name(vk, campaign):
    cab_name, cli_name = None, None
    cab_id, cli_id = campaign.cabinet_id, campaign.client_id
    cabinets, _ = vk.get_cabs_and_groups()
    if cabinets:
        for cab in cabinets:
            if cab['account_id'] == cab_id:
                cab_name = cab['account_name']
                if cli_id and cab['client_id'] == cli_id:
                    cli_name = cab['client_name']
                    break

    campaign.cabinet_name = cab_name
    campaign.client_name = cli_name
    campaign.save()
    db.connections.close_all()
