from vk.engine import VkEngine
from vk.related import utils


class VkRelatedParser(VkEngine):

    def get_artist_card(self, artist_url):
        resp = self._api_response('catalog.getAudioArtist', {'url': artist_url, 'need_blocks': 1})
        if resp:
            return resp

    def get_related_links(self, card_obj):
        related_block_id = utils.pars_related_block_id_from_card_obj(card_obj)
        if related_block_id:
            resp = self._api_response('catalog.getBlockItems', {'block_id': related_block_id})
            if resp and 'links' in resp.keys():
                return resp['links']

    def get_related_cards(self, related_links):
        if related_links:
            code = utils.code_for_get_related_cards(related_links)
            resp = self._execute_response(code)
            if resp:
                return resp

    def scroll_artist_card(self, artist_card):
        related_block_id = utils.pars_related_block_id_from_card_obj(artist_card)
        if not related_block_id:
            section_id, next_from = utils.pars_artist_card_section_id_and_next_from(artist_card)
            if section_id and next_from:
                resp_2 = self._api_response('catalog.getSection', {'section_id': section_id, 'start_from': next_from})
                try:
                    artist_card['catalog']['sections'][0]['blocks'].extend(resp_2['section']['blocks'])
                    return artist_card
                except (KeyError, IndexError):
                    return None
        else:
            return artist_card

    def recurse_get_related_cards(self, artist_card, listens=25000, n_releases=5, last_days=60, median_days=60,
                                  max_recurse=2, current_recurse=1, genres=None):

        artist_card = self.scroll_artist_card(artist_card)
        if artist_card:
            related_links = self.get_related_links(artist_card)
            related_cards = self.get_related_cards(related_links)
            filtered_cards = utils.filter_artist_cards(related_cards, listens, n_releases, last_days, median_days, genres)
            if isinstance(related_cards, list) and current_recurse <= max_recurse:
                for card in related_cards:
                    filtered_cards.extend(self.recurse_get_related_cards(card, listens, n_releases, last_days, median_days,
                                                                         max_recurse, current_recurse=current_recurse + 1))
            return filtered_cards
        else:
            return []

    def get_related_artists(self, artist_url, listens=25000, n_releases=5, last_days=60, median_days=60, max_recurse=2):
        artist_card = self.get_artist_card(artist_url)
        if artist_card:
            artist_name, _, photo_url = utils.get_artist_info_from_card_obj(artist_card)
            genres = utils.get_genres_from_releases(artist_card['releases']) if 'releases' in artist_card.keys() else None
            related_cards = self.recurse_get_related_cards(artist_card, listens, n_releases, last_days, median_days,
                                                           max_recurse, current_recurse=1, genres=genres)
            simple_cards = utils.simplify_artist_cards(related_cards)
            simple_cards = utils.clean_doubles_in_simple_cards(simple_cards, artist_name)
            result = {'artist_name': artist_name, 'photo_url': photo_url, 'related': simple_cards}
            return result
