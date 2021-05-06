import django.db.utils
import sqlite3
import time
import datetime
import statistics
import numpy as np

from datetime import datetime, timedelta, date

import pytz
from django.utils import timezone

from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, get_list_or_404

from .models import Chart, Position, Track
from .serializers import ChartSerializer, TrackForSearchSerializer, TrackForSearchExtendedSerializer
from mooscle.parser import MooscleParser
from api.settings import CHARTS_FULL_NAMES


def get_chart(service, date=None):
    if not date:
        date = timezone.now().date()

    chart = get_object_or_404(Chart, date=date, service=service)
    return ChartSerializer(chart).data


def get_all_charts(date=None):
    if not date:
        date = timezone.now().date()

    chart = get_list_or_404(Chart, date=date)
    return ChartSerializer(chart, many=True).data


def add_chart(service, date):
    try:
        existed_chart = Chart.objects.filter(date=date, service=service).first()
        if not existed_chart:
            date_str = str(date.strftime("%d.%m.%Y"))
            charts = MooscleParser()
            result = charts.get_one(service=service, date=date_str)
            if result and result[service]:
                chart_orm_obj = Chart.objects.create(date=date, service=service)
                for item in result[service]:
                    _pars_chart_item(item, chart_orm_obj)
            chart = Chart.objects.filter(date=date, service=service).first()
        else:
            chart = existed_chart

        if chart:
            return ChartSerializer(chart).data
        return {'detail': f'Not found chart {service} for date {date}'}

    except sqlite3.OperationalError:
        return add_chart(service, date)


def _pars_chart_item(item, chart_orm_obj):
    try:
        if _check_item(item):

            position_current = int(item['position'])
            position_prev = None
            position_delta = None

            track = Track.objects.filter(artist=item['artist'], title=item['title']).first()
            if track:
                prev_date = chart_orm_obj.date - timedelta(days=1)
                prev_chart = Chart.objects.filter(service=chart_orm_obj.service, date=prev_date).first()
                if prev_chart:
                    prev_pos = prev_chart.positions.filter(track=track).first()
                    if prev_pos:
                        position_prev = prev_pos.current
                        position_delta = position_prev - position_current
            else:
                track = Track.objects.create(
                    artist=item['artist'],
                    title=item['title'],
                    cover_url=item['cover'] if item['cover'] else None,
                    has_cover=True if item['cover'] else False,
                    distributor=item['distributor'] if item['distributor'] else None,
                    has_distributor=True if item['distributor'] else False
                )

            position = Position.objects.create(
                chart=chart_orm_obj,
                service=chart_orm_obj.service,
                date=chart_orm_obj.date,
                current=position_current,
                previous=position_prev,
                delta=position_delta
            )

            track.positions.add(position)

    except (sqlite3.OperationalError, django.db.utils.OperationalError):
        time.sleep(3)
        _pars_chart_item(item, chart_orm_obj)


def _check_item(item):
    keys = 'artist', 'title', 'cover', 'distributor'
    if item:
        if all([True if x in item.keys() else False for x in keys]):
            if item['artist'] and item['title']:
                return True


def search(artist=None, title=None, extended=False, date_from=None, date_to=None):
    dates = get_dates_list(date_from, date_to)

    if artist and title:
        tracks = Track.objects.filter(artist__icontains=artist,
                                      title__icontains=title,
                                      positions__date__in=dates)\
                              .annotate(positions_count=Count('positions'))\
                              .order_by('-positions_count')
    elif artist:
        tracks = Track.objects.filter(artist__icontains=artist, positions__date__in=dates)\
                              .annotate(positions_count=Count('positions'))\
                              .order_by('-positions_count')
    elif title:
        tracks = Track.objects.filter(title__icontains=title, positions__date__in=dates)\
                              .annotate(positions_count=Count('positions'))\
                              .order_by('-positions_count')
    else:
        return {'error': 'artist or title required'}

    context = {'dates': dates}
    if extended:
        return TrackForSearchExtendedSerializer(tracks, many=True, context=context).data
    else:
        return TrackForSearchSerializer(tracks, many=True, context=context).data


def get_top_by_days(service, top=50, extended=False, reverse=False, date_from=None, date_to=None):
    if reverse:
        ordering = 'positions_count'
    else:
        ordering = '-positions_count'

    dates = get_dates_list(date_from, date_to)

    tracks = Track.objects.filter(positions__service=service, positions__date__in=dates)\
                          .annotate(positions_count=Count('positions'))\
                          .order_by(ordering)[:top]

    context = {'service': service, 'reverse': reverse, 'dates': dates}
    if extended:
        return TrackForSearchExtendedSerializer(tracks, many=True, context=context).data
    else:
        return TrackForSearchSerializer(tracks, many=True, context=context).data


def get_top_by_deltas(service, top=50, extended=False, reverse=False, date_from=None, date_to=None):
    if reverse:
        ordering = 'max_position_delta'
    else:
        ordering = '-max_position_delta'

    dates = get_dates_list(date_from, date_to)

    tracks = Track.objects.filter(positions__service=service,
                                  positions__date__in=dates,
                                  positions__delta__isnull=False)\
                          .annotate(max_position_delta=Max('positions__delta'))\
                          .order_by(ordering)[:top]

    context = {'service': service, 'reverse': reverse, 'deltas': True}
    if extended:
        return TrackForSearchExtendedSerializer(tracks, many=True, context=context).data
    else:
        return TrackForSearchSerializer(tracks, many=True, context=context).data


def get_chart_stats(service, date_from=None, date_to=None):
    dates = get_dates_list(date_from, date_to)

    tracks = Track.objects.filter(positions__service=service, positions__date__in=dates)\
                          .annotate(Count('positions'))

    days_in_chart = [track.positions__count for track in tracks]

    stats = {
        'service': CHARTS_FULL_NAMES[service],
        'quantile_25': int(np.quantile(days_in_chart, 0.25)),
        'quantile_50': int(np.quantile(days_in_chart, 0.50)),
        'quantile_75': int(np.quantile(days_in_chart, 0.75)),
        'quantile_95': int(np.quantile(days_in_chart, 0.95)),
        'mean': round(statistics.mean(days_in_chart)),
        'stdev': statistics.stdev(days_in_chart),
        'variance': statistics.variance(days_in_chart)
    }

    return stats


def del_duplicate_positions():
    position_fileds = ['service', 'date', 'current', 'previous', 'delta']
    remove_duplicated_records(Position, position_fileds)


def remove_duplicated_records(model, fields):
    """
    Removes records from `model` duplicated on `fields`
    while leaving the most recent one (biggest `id`).
    """
    duplicates = model.objects.values(*fields)

    # override any model specific ordering (for `.annotate()`)
    duplicates = duplicates.order_by()

    # group by same values of `fields`; count how many rows are the same
    duplicates = duplicates.annotate(
        max_id=Max("id"), count_id=Count("id")
    )

    # leave out only the ones which are actually duplicated
    duplicates = duplicates.filter(count_id__gt=1)

    for duplicate in duplicates:
        to_delete = model.objects.filter(**{x: duplicate[x] for x in fields})

        # leave out the latest duplicated record
        # you can use `Min` if you wish to leave out the first record
        to_delete = to_delete.exclude(id=duplicate["max_id"])

        to_delete.delete()


def get_track(service, id):
    track = get_object_or_404(Track, id=id)
    context = {'service': service, 'reverse': False}
    return TrackForSearchExtendedSerializer(track, context=context).data


def get_dates_list(date_from=None, date_to=None):
    if not date_from:
        date_from = date(year=2018, month=7, day=20)
    if not date_to:
        date_to = date.today()

    return [_date_from_plus_timedelta(date_from, x) for x in range(0, (date_to - date_from).days + 1)]


def _date_from_plus_timedelta(date_from, days):
    res = date_from + timezone.timedelta(days=days)
    res = datetime.combine(res, datetime.min.time())
    utc = pytz.utc
    res = utc.localize(res)
    return res


def pack_search_result(result):
    packed_items = []
    for item in result:
        if 'positions' not in item.keys():
            packed_items.append(item)
            continue

        packed_positions = {}
        for position in item['positions']:
            if position['service'] not in packed_positions.keys():
                packed_positions[position['service']] = [position]
            else:
                packed_positions[position['service']].append(position)

        for positions in packed_positions.values():
            positions.reverse()

        dict_to_list = [{'service': service, 'positions': positions} for service, positions in packed_positions.items()]
        dict_to_list.sort(key=lambda x: x['service'])

        item['positions'] = dict_to_list
        packed_items.append(item)

    return packed_items
