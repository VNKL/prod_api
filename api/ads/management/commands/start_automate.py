from time import sleep
from datetime import datetime, timedelta, time
from django.utils import timezone
from django import db

from django.core.management.base import BaseCommand

from api.ads.models import Ad, Automate
from vk.ads.ads import VkAds
from api.ads.utils import update_campaign_stats


class Command(BaseCommand):
    help = 'start new automate'

    def add_arguments(self, parser):
        parser.add_argument('-automate_id', action='store', dest='automate_id', type=int)

    def handle(self, *args, **options):
        if 'automate_id' not in options.keys():
            print('automate_id is required to start_automate command')
        else:
            start_automate(options['automate_id'])


def start_automate(automate_id):

    automate = Automate.objects.filter(pk=automate_id).first()
    if not automate:
        print(f'no automate with id {automate_id}')
    else:
        _start_automate(automate)


def _start_automate(automate):
    _del_existed_automates(automate)

    campaign = automate.campaign
    vk = VkAds(campaign.owner.ads_token)
    vk.update_campaign(campaign.cabinet_id, campaign.campaign_id, start=True)
    campaign.is_automate = True
    campaign.save()

    if campaign.has_moderate_audios and automate.type == 0:
        automate.status = 3
        automate.error = f"{campaign} can't be automate with type 'listens'"
        automate.save()
        campaign.is_automate = False
        campaign.save()
        return

    _wait_for_start_time(automate)
    finish_time = _get_finish_time(automate)

    ads = Ad.objects.filter(campaign=campaign)
    db.connections.close_all()
    vk.update_ads(cabinet_id=campaign.cabinet_id, ad_ids=[x.ad_id for x in ads], money_limit=0)

    next_update_time = datetime.now() - timedelta(minutes=15)
    while datetime.now() < finish_time:
        automate = Automate.objects.filter(pk=automate.pk).first()
        db.connections.close_all()
        if automate and automate.status == 0:
            break
        elif not automate:
            break

        if datetime.now() > next_update_time:
            campaign.refresh_from_db()
            campaign, money_limit = update_campaign_stats(campaign)
            _update_ads(campaign, automate, vk)
            db.connections.close_all()
            next_update_time = datetime.now() + timedelta(minutes=15)
            if campaign.spent == money_limit or campaign.status == 2:
                break

        sleep(60)

    if automate:
        _stop_ads(campaign, vk)
        vk.update_campaign(campaign.cabinet_id, campaign.campaign_id, stop=True)
        campaign.is_automate = False
        campaign.save()
        automate.status = 0
        automate.finish_date = timezone.now()
        automate.save()

    db.connections.close_all()


def _del_existed_automates(automate):
    existed_automates = Automate.objects.filter(campaign=automate.campaign)
    if existed_automates:
        for item in existed_automates:
            if item.pk != automate.pk:
                item.delete()


def _wait_for_start_time(automate):
    if automate.start == 1:
        start_time = datetime.combine(datetime.now().date(), time(0, 0)) + timedelta(days=1)
        while datetime.now() < start_time:
            sleep(60)
    automate.status = 1
    automate.save()


def _get_finish_time(automate):
    if automate.finish == 0:
        return datetime.combine(datetime.now().date(), time(0, 0)) + timedelta(days=1) - timedelta(minutes=1)
    else:
        return datetime.combine(datetime.now().date(), time(0, 0)) + timedelta(days=365)


def _update_ads(campaign, automate, vk):
    automate_type, target_cost, stop_cost = automate.type, automate.target_cost, automate.target_cost * 1.2

    ads = Ad.objects.filter(campaign=campaign)

    to_start, to_stop, to_update_cpm, cpm_list, updated_ads = [], [], [], [], []
    for ad in ads:
        if 'Пустой сегмент' in ad.ad_name:
            continue

        if automate_type == 0:
            current_cost = ad.cpl
        else:
            current_cost = ad.cps

        _do_ads_update_logic(ad, cpm_list, current_cost, stop_cost, target_cost, to_start, to_stop, to_update_cpm,
                             updated_ads)

    if to_start:
        vk.update_ads(cabinet_id=campaign.cabinet_id, ad_ids=to_start, start=True)

    if to_stop:
        vk.update_ads(cabinet_id=campaign.cabinet_id, ad_ids=to_stop, stop=True)

    if to_update_cpm:
        vk.update_ads(cabinet_id=campaign.cabinet_id, ad_ids=to_update_cpm, cpm_list=cpm_list)

    if updated_ads:
        Ad.objects.bulk_update(updated_ads, fields=['status'], batch_size=40)

    db.connections.close_all()


def _do_ads_update_logic(ad, cpm_list, current_cost, stop_cost, target_cost, to_start, to_stop, to_update_cpm,
                         updated_ads):

    step = 3.3

    if current_cost == 0:
        to_stop.append(ad.ad_id)
        ad.status = 0
        updated_ads.append(ad)

    elif current_cost > stop_cost and ad.status == 1:
        to_stop.append(ad.ad_id)
        ad.status = 0
        updated_ads.append(ad)

    elif current_cost < stop_cost and ad.status == 0:
        ad.status = 1
        to_start.append(ad.ad_id)
        to_update_cpm.append(ad.ad_id)
        cpm = ad.cpm_price - step if ad.cpm_price - step > 30 else 30
        cpm_list.append(cpm)
        updated_ads.append(ad)

    elif target_cost < current_cost < stop_cost and ad.status == 1:
        to_update_cpm.append(ad.ad_id)
        cpm = ad.cpm_price - step if ad.cpm_price - step > 30 else 30
        cpm_list.append(cpm)
        updated_ads.append(ad)

    elif current_cost < target_cost:
        to_update_cpm.append(ad.ad_id)
        cpm = ad.cpm_price + step if ad.cpm_price + step < 120 else 120
        cpm_list.append(cpm)
        updated_ads.append(ad)


def _stop_ads(campaign, vk):
    ads = Ad.objects.filter(campaign=campaign)
    ad_ids = [x.ad_id for x in ads]
    vk.update_ads(cabinet_id=campaign.cabinet_id, ad_ids=ad_ids, stop=True)
