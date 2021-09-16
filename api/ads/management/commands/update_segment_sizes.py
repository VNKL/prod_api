from django.core.management.base import BaseCommand
from django import db

from api.ads.models import Campaign, Ad
from vk.ads.ads import VkAds


class Command(BaseCommand):
    help = 'update campaign segments sizes'

    def add_arguments(self, parser):
        parser.add_argument('-campaign_id', action='store', dest='campaign_id', type=int)

    def handle(self, *args, **options):
        if 'campaign_id' not in options.keys():
            print('campaign_id is required to update_segment_sizes command')
        else:
            update_segments(options['campaign_id'])


def update_segments(campaign_id):

    campaign = Campaign.objects.filter(campaign_id=campaign_id).first()
    if not campaign:
        print(f'no campaign with id {campaign_id}')
    else:
        update_campaign_segment_sizes(campaign)
    db.connections.close_all()


def update_campaign_segment_sizes(campaign):
    token = campaign.owner.ads_token
    if not token:
        return campaign

    ads = Ad.objects.filter(campaign=campaign)
    if not ads:
        return campaign

    vk = VkAds(token)
    updated_ads = []
    for ad in ads:
        audience_count = vk.get_segment_size(cabinet_id=campaign.cabinet_id,
                                             client_id=campaign.client_id,
                                             ad_id=ad.ad_id,
                                             post_url=f"https://vk.com/wall-{ad.post_owner}_{ad.post_id}")
        if audience_count:
            ad.audience_count = audience_count
            updated_ads.append(ad)

    if updated_ads:
        Ad.objects.bulk_update(updated_ads, fields=['audience_count'], batch_size=40)

    ads = Ad.objects.filter(campaign=campaign)
    campaign_audience_count = 0
    for ad in ads:
        if ad.audience_count and 'Пустой сегмент' not in ad.ad_name:
            campaign_audience_count += ad.audience_count

    if campaign_audience_count:
        campaign.audience_count = campaign_audience_count
        campaign.save()

    db.connections.close_all()
