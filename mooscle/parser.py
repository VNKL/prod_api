import requests
from bs4 import BeautifulSoup

from . import utils


class MooscleParser:

    def __init__(self):
        self.session = requests.session()

    def get_one(self, service, date=None):
        tracks = []
        service_id = utils.convert_service_id(service)
        for url in utils.compile_mooscle_urls(service_id, date):
            chart_batch = self._get_mooscle_chart_batch(url, service_id)
            tracks.extend(utils.pars_mooscle_chart_batch(chart_batch))

        if tracks:
            print(f'Parsing chart {service} for date {date}: success')
        else:
            print(f'Parsing chart {service} for date {date}: fail')

        return {service: tracks}

    def get_many(self, services, date=None):
        result = {}
        for service in services:
            result.update(self.get_one(service, date))
        return result

    def get_one_period(self, service, date_from, date_to):
        dates_list = utils.dates_period_to_list(date_from, date_to)
        result = {}
        for date in dates_list:
            result[date] = self.get_one(service, date)
        return result

    def get_many_period(self, services, date_from, date_to):
        dates_list = utils.dates_period_to_list(date_from, date_to)
        result = {}
        for date in dates_list:
            result[date] = self.get_many(services, date)
        return result

    def _get_mooscle_chart_batch(self, url, service_id):
        try:
            if 'admin-ajax.php' in url:
                html = self.session.get(url).json()['content']
                track_list = BeautifulSoup(html, 'lxml')
            else:
                html = self.session.get(url).text
                soup = BeautifulSoup(html, 'lxml')
                track_list = soup.find(id=service_id)
            return track_list
        except Exception:
            return []
