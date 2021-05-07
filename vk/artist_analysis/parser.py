from datetime import datetime, date, timedelta

from vk.engine import VkEngine
from vk.audio_savers.parser import AudioSaversParser
from vk.artist_analysis import utils


class ArtistCardParser(VkEngine):

    def get_by_artist_url(self, artist_card_url, n_top=3, n_last=3):
        """
        Возвращает дикт с результатами анализа артиста

        :param artist_card_url:     str, ссылка на карточку артиста в ВК
        :param n_top:               int, кол-во топ треков, которые будут использоваться при анализе артиста
        :param n_last:              int, кол-во последних релизов, которые будут использованы при анализе артиста
        :return:                    dict, дикт с результатами анализа
        """
        card = self.get_artist_card(artist_card_url)
        analysis = self.analize_artist_card(card, n_top=n_top, n_last=n_last)
        analysis = self.extend_by_audio_savers(analysis, artist_card_url, n_top=n_top)
        analysis = self.extend_by_charts(analysis)

        return analysis

    def extend_by_audio_savers(self, analysis, artist_card_url, n_top=3):
        analysis = analysis.copy()
        audio_savers_parser = AudioSaversParser()
        audios = audio_savers_parser.get_by_artist_url(artist_card_url, count_only=True)
        top_audios, all_savers_count = utils.process_audios_with_savers(audios, n_top=n_top)
        if top_audios:
            analysis['analysis']['top']['top_saving_tracks'] = top_audios
            analysis['analysis']['sum']['all_tracks_savers_count'] = all_savers_count
        return analysis

    def extend_by_charts(self, analysis, n_top=3):
        analysis = analysis.copy()
        artist = analysis['analysis']['artist']['artist_name']

        date_from_last_year = date.today() - timedelta(days=365)
        date_from_last_90 = date.today() - timedelta(days=90)
        date_from_now = date.today() - timedelta(days=1)

        all_time, pos_medians = utils.search_chart_releases(artist=artist)
        last_365, _ = utils.search_chart_releases(artist=artist, date_from=date_from_last_year)
        last_90, _ = utils.search_chart_releases(artist=artist, date_from=date_from_last_90)
        now, _ = utils.search_chart_releases(artist=artist, date_from=date_from_now)

        top_by_days, top_by_pos, days_medians = utils.calculate_tops_of_artist_by_chart(all_time, n_top=n_top)

        analysis['analysis'].update({'charts': {'all_time': all_time,
                                                'last_365': last_365,
                                                'last_90': last_90,
                                                'now': now,
                                                'top_by_days': top_by_days,
                                                'top_by_positions': top_by_pos,
                                                'days_medians': days_medians,
                                                'positions_medians': pos_medians}})

        return analysis

    def get_artist_card(self, artist_id_or_url):
        params = {'url': artist_id_or_url} if 'vk.com' in artist_id_or_url else {'artist_id': artist_id_or_url}
        params.update({'need_blocks': 1})
        resp = self._api_response('catalog.getAudioArtist', params)
        if resp and '{artist_name}' not in resp['catalog']['sections'][0]['title']:
            return resp
        else:
            self.errors.append({'method': 'api/analysis.getByArtist', 'param': artist_id_or_url,
                                'error_msg': 'Artist card is not recieved, card may does not exist'})

    def get_artist_videos(self, artist_card_obj):
        block_id = utils.find_block_id(artist_card_obj, block_name='videos')
        if block_id:
            return self._get_artist_videos(block_id)

    def analize_artist_card(self, card, n_top=3, n_last=3):
        artist_name, artist_id = utils.pars_artist_from_card(card)  # str, int
        singles, albums = utils.pars_playlists_from_card(card)  # list of vk playlist objects
        singles_freq, albums_freq = utils.calculate_release_freq(singles, albums)  # int, int (days)
        sl_min, sl_max, sl_median, sl_sum = utils.calculate_listens(singles)
        sf_min, sf_max, sf_median, sf_sum = utils.calculate_follows(singles)
        al_min, al_max, al_median, al_sum = utils.calculate_listens(albums)
        af_min, af_max, af_median, af_sum = utils.calculate_follows(albums)
        top_listen_singles, top_follow_singles = utils.calculate_top_listens_and_followers(singles, n_top=n_top)
        top_listen_albums, top_follow_albums = utils.calculate_top_listens_and_followers(albums, n_top=n_top)
        top_streams = utils.pars_top_streams_tracks(card, n_top=n_top, simplyfy=True)  # list of vk audio objects
        last_top_date, n_after_top, last_release_date = utils.calculate_after_last_top(card, n_top=n_top)
        videos = self.get_artist_videos(card)  # list of vk video objects
        vv_min, vv_max, vv_median, vv_sum = utils.calculate_video_views(videos)  # int, int, int, int
        links = utils.get_artist_links(card)  # list of vk link objects
        links = self._get_followers_counts(links)  # links with type and followers

        return {
            'parsing_date': datetime.now(),
            'analysis': {
                'artist': {
                    'artist_name': artist_name,
                    'artist_id': artist_id,
                    'links': [utils.simplify_link_obj(x) for x in links] if links else [],
                    'related': self._get_related(card),
                },
                'singles': {
                    'items': [utils.simplify_playlist_obj(x) for x in singles] if singles else [],
                    'count': len(singles) if singles else 0,
                    'freq': singles_freq,
                    'listens_min': sl_min,
                    'listens_max': sl_max,
                    'listens_median': sl_median,
                    'listens_sum': sl_sum,
                    'followers_min': sf_min,
                    'followers_max': sf_max,
                    'followers_median': sf_median,
                    'followers_sum': sf_sum,
                },
                'albums': {
                    'items': [utils.simplify_playlist_obj(x) for x in albums] if albums else [],
                    'count': len(albums) if albums else 0,
                    'freq': albums_freq,
                    'listens_min': al_min,
                    'listens_max': al_max,
                    'listens_median': al_median,
                    'listens_sum': al_sum,
                    'followers_min': af_min,
                    'followers_max': af_max,
                    'followers_median': af_median,
                    'followers_sum': af_sum,
                },
                'videos': {
                    'items': [utils.simplify_video_obj(x) for x in videos] if videos else [],
                    'count': len(videos) if videos else 0,
                    'freq': utils.calculate_videos_freq(videos),
                    'views_min': vv_min,
                    'views_max': vv_max,
                    'views_median': vv_median,
                    'views_sum': vv_sum,
                },
                'genres': {
                    'all_releases_genres': utils.pars_genres(card),
                    'last_releases_genres': utils.pars_genres(card, n_last=n_last),
                    'top_releases_genres': utils.pars_genres(card, n_top=n_top),
                },
                'top': {
                    'top_streaming_tracks': top_streams,
                    'top_saving_tracks': None,
                    'top_listening_singles': top_listen_singles,
                    'top_listening_albums': top_follow_albums,
                    'top_following_singles': top_follow_singles,
                    'top_following_albums': top_follow_albums,
                },
                'sum': {
                    'all_releases_listens': sl_sum if sl_sum else 0 + al_sum if al_sum else 0,
                    'all_releases_followers': sf_sum if sf_sum else 0 + sf_sum if sf_sum else 0,
                    'all_tracks_count': utils.calculate_all_tracks_count([singles, albums]),
                    'all_tracks_savers_count': None,
                },
                'last': {
                    'last_release_date': last_release_date,
                    'last_top_release_date': last_top_date,
                    'after_top_releases_count': n_after_top,
                },
            }
        }

    def _get_artist_videos(self, block_id, next_from=None):
        videos = []
        resp = self._api_response('catalog.getBlockItems', {'block_id': block_id, 'start_from': next_from})
        if resp:
            if 'artist_videos' in resp.keys():
                videos.extend(resp['artist_videos'])
            if 'block' in resp.keys() and 'next_from' in resp['block'].keys():
                videos.extend(self._get_artist_videos(block_id, next_from=resp['block']['next_from']))
        return videos

    def _get_related(self, card):
        block_id = utils.find_block_id(card, block_name='related')
        if block_id:
            return self._pars_related_block(block_id)

    def _pars_related_block(self, block_id, next_from=None):
        related_urls = []
        resp = self._api_response('catalog.getBlockItems', {'block_id': block_id, 'start_from': next_from})
        if resp:
            for link in resp['links']:
                related_urls.append({'artist': link['title'], 'url': link['url']})
            if 'next_from' in resp['block'].keys():
                related_urls.extend(self._pars_related_block(block_id=block_id, next_from=resp['block']['next_from']))
        return related_urls

    def _get_followers_counts(self, links):

        links = links.copy()

        for link in links:
            item_url = link['url']
            item_id = None

            if 'https://vk.com/public' in item_url:
                item_id = item_url.replace('https://vk.com/public', '')
            elif 'https://vk.com/' in item_url:
                item_id = item_url.replace('https://vk.com/', '')

            if item_id:
                resp = self._api_response('groups.getMembers', {'group_id': item_id, 'count': 1})
                if resp and 'count' in resp.keys():
                    link.update({'type': 'group', 'followers': resp['count']})
                else:
                    resp = self._api_response('users.get', {'user_ids': 'mmott'})
                    if resp:
                        user_id = resp[0]['id']
                        resp = self._api_response('users.getFollowers', {'user_id': user_id, 'count': 1})
                        if resp and 'count' in resp.keys():
                            link.update({'type': 'user_page', 'followers': resp['count']})

        return links
