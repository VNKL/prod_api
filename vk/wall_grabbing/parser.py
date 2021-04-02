from datetime import date

from vk.engine import VkEngine
from . import utils


class WallParser(VkEngine):

    def __init__(self):
        super().__init__()
        self.owner_id = None
        self.all_posts_count = None
        self.current_offset = 100
        self.is_offset_limited = False

    def get_group_posts(self, group, date_from=None, date_to=None, with_audio=False,
                        with_dark_posts=False, dark_posts_only=False, pars_playlists=True,
                        pars_audio_savers=True):

        posts = self.get_wall_posts(group, date_from, date_to, wall_type='group')

        if dark_posts_only:
            dark_posts = self.get_dark_posts(posts)
            result_posts = self._filter_posts_by_dates(dark_posts, date_from, date_to)
        elif with_dark_posts:
            dark_posts = self.get_dark_posts(posts)
            dark_posts = self._filter_posts_by_dates(dark_posts, date_from, date_to)
            result_posts = posts + dark_posts
        else:
            result_posts = posts

        if with_audio:
            posts = self._filter_posts_by_has_audio(result_posts, pars_playlists)
        else:
            posts = self._get_audios_from_playlists(result_posts)

        if pars_audio_savers:
            posts = self._get_post_audios_savers(posts)
            posts = self._get_post_playlist_listens(posts)

        return self._get_post_playlist_listens(posts)

    def get_user_posts(self, user, date_from=None, date_to=None, with_audio=False, pars_playlists=False):
        posts = self.get_wall_posts(user, date_from, date_to, wall_type='user')
        posts = self._filter_posts_by_has_audio(posts, pars_playlists) if with_audio else posts
        posts = self._get_post_audios_savers(posts)
        return self._get_post_playlist_listens(posts)

    def get_wall_posts(self, owner_url, date_from, date_to, wall_type):
        owner_id = self._get_owner_id(owner_url, wall_type)
        if owner_id:
            self.owner_id = owner_id
            actual_wall = self._api_response('wall.get', {'owner_id': f'{owner_id}', 'count': 100})
            if actual_wall:
                self.all_posts_count = actual_wall['count']
                return self._filter_posts_by_dates(actual_wall['items'], date_from, date_to, auto_scroll=True)

    def get_dark_posts(self, posts):
        posts_ids = [x['id'] for x in posts]
        if not posts_ids:
            return []

        posts_interval = [x for x in range(min(posts_ids), max(posts_ids) + 1) if x not in posts_ids]
        adding_posts = list(range(max(posts_ids), max(posts_ids) + 1000))

        dark_posts = self._execute_get_posts_by_ids(self.owner_id, posts_interval)
        dark_posts.extend(self._execute_get_posts_by_ids(self.owner_id, adding_posts))

        return dark_posts

    def _execute_get_posts_by_ids(self, group_id, post_ids):

        n, batch, ids_batches = 0, [], []
        for post_id in post_ids:
            if n == 100:
                ids_batches.append(batch)
                batch = []
                n = 0
            batch.append(post_id)
            n += 1
        ids_batches.append(batch)

        posts = []
        for x in range(0, len(ids_batches), 10):
            y = x + 10 if len(ids_batches) > x + 10 else None
            code = utils.code_for_get_by_id(group_id, ids_batches[x:y])
            resp = self._execute_response(code)
            if resp:
                for batch_resp in resp:
                    for post in batch_resp:
                        if isinstance(post, dict) and post['post_type'] == 'post_ads':
                            posts.append(post)

        return posts

    def _filter_posts_by_dates(self, posts, date_from, date_to, auto_scroll=False):
        if not posts:
            return []

        filtered_posts = []
        posts_list_slice = 0
        if 'is_pinned' in posts[0].keys():
            posts_list_slice = 1
            post_date = date.fromtimestamp(posts[0]['date'])
            if utils.check_date_in_period(post_date, date_from, date_to):
                filtered_posts.append(posts[0])

        for post in posts[posts_list_slice:]:
            post_date = date.fromtimestamp(post['date'])
            if utils.check_date_in_period(post_date, date_from, date_to):
                filtered_posts.append(post)

        if auto_scroll:
            if filtered_posts and filtered_posts[-1] == posts[-1] or not filtered_posts:
                new_posts = self._get_next_wall_batch()
                if new_posts:
                    filtered_posts.extend(self._filter_posts_by_dates(new_posts, date_from, date_to))

        return filtered_posts

    def _filter_posts_by_has_audio(self, posts, pars_playlists=False):
        if not posts:
            return posts

        posts_with_audio = []
        for post in posts:
            if 'attachments' in post.keys():
                for attach in post['attachments']:
                    if attach['type'] == 'audio':
                        posts_with_audio.append(post)
                        break
                    elif attach['type'] == 'link' and 'audio?act=audio_playlist' in attach['link']['url']:
                        posts_with_audio.append(post)

        if pars_playlists:
            return self._get_audios_from_playlists(posts_with_audio)

        return posts_with_audio

    def _get_audios_from_playlists(self, posts_with_playlist):
        processed_posts = []
        for post in posts_with_playlist:
            pl_url = [x['link']['url'] for x in post['attachments'] if
                      x['type'] == 'link' and 'playlist' in x['link']['url']]
            pl_title = [x['link']['title'] for x in post['attachments'] if
                        x['type'] == 'link' and 'playlist' in x['link']['url']]
            if not pl_url:
                processed_posts.append(post)
                continue

            pl_owner, pl_id, ac_hash = utils.pars_playlist_params_from_url(pl_url[0])
            post = post.copy()
            post['attachments'].append({'type': 'playlist',
                                        'playlist': {'owner_id': pl_owner,
                                                     'id': pl_id,
                                                     'access_hash': ac_hash,
                                                     'title': pl_title[0] if pl_title else None}})

            resp = self._api_response('execute.getPlaylist', {'owner_id': pl_owner, 'id': pl_id, 'access_key': ac_hash})
            if resp and 'audios' in resp.keys():
                for audio in resp['audios']:
                    audio = audio.copy()
                    audio['source'] = 'playlist'
                    post['attachments'].append({'type': 'audio', 'audio': audio})

            processed_posts.append(post)

        return processed_posts

    def _get_next_wall_batch(self):
        if self.is_offset_limited or self.current_offset > self.all_posts_count:
            return []

        code = utils.code_for_get_wall(owner_id=self.owner_id, offset=self.current_offset)
        resp = self._execute_response(code)
        new_posts = []
        for wall in resp:
            if wall and 'items' in wall.keys():
                new_posts.extend(wall['items'])

        if not resp[-1]:
            self.is_offset_limited = True
        else:
            self.current_offset += 1000

        return new_posts

    def _get_group_id(self, group):
        if isinstance(group, int):
            return group

        try:
            return int(group)
        except ValueError:
            if 'https://vk.com/public' in group:
                group = group.replace('https://vk.com/public', '')
                return int(group)
            elif 'https://vk.com/' in group:
                screen_name = group.replace('https://vk.com/', '')
                resp = self._api_response('utils.resolveScreenName', {'screen_name': screen_name})
                if resp and resp['type'] == 'group':
                    return resp['object_id']

    def _get_user_id(self, user):
        if isinstance(user, int):
            return user

        try:
            return int(user)
        except ValueError:
            if 'https://vk.com/public' in user:
                user = user.replace('https://vk.com/id', '')
                return int(user)
            elif 'https://vk.com/' in user:
                screen_name = user.replace('https://vk.com/', '')
                resp = self._api_response('utils.resolveScreenName', {'screen_name': screen_name})
                if resp and resp['type'] == 'user':
                    return resp['object_id']

    def _get_owner_id(self, owner_url, wall_type):
        if wall_type == 'group':
            owner_id = self._get_group_id(owner_url)
            if owner_id:
                owner_id = 0 - owner_id
        elif wall_type == 'user':
            owner_id = self._get_user_id(owner_url)
        else:
            raise AttributeError("wall_type must be 'group' or 'user'")
        return owner_id

    def _get_post_audios_savers(self, posts):
        many_audios, one_audio, without_audio = utils.filter_posts_for_audio_savers(posts)

        if one_audio:
            for x in range(0, len(one_audio), 25):
                y = x + 25 if len(one_audio) > x + 25 else None
                code = utils.code_for_get_posts_audio_savers_count(one_audio[x:y])
                resp = self._execute_response(code)
                if resp:
                    for n, post in enumerate(one_audio[x:y]):
                        for attach in post['attachments']:
                            if attach['type'] == 'audio':
                                attach['audio']['savers_count'] = resp[n]

        if many_audios:
            for post in many_audios:
                code = utils.code_for_get_post_audios_savers_count(post)
                resp = self._execute_response(code)
                if resp:
                    n = 0
                    for attach in post['attachments']:
                        if attach['type'] == 'audio':
                            attach['audio']['savers_count'] = resp[n]
                            n += 1

        return one_audio + many_audios + without_audio

    def _get_post_playlist_listens(self, post):
        with_playlist, without_playlist = utils.filter_post_by_has_playlist(post)

        if with_playlist:
            for x in range(0, len(with_playlist), 25):
                y = x + 25 if len(with_playlist) > x + 25 else None
                code = utils.code_for_get_playlists_listens(with_playlist[x:y])
                resp = self._execute_response(code)
                if resp:
                    for n, post in enumerate(with_playlist[x:y]):
                        for attach in post['attachments']:
                            if attach['type'] == 'playlist':
                                attach['playlist']['listens'] = resp[n]['plays']
                                attach['playlist']['followers'] = resp[n]['followers']
                                attach['playlist']['create_time'] = resp[n]['create_time']
                                attach['playlist']['update_time'] = resp[n]['update_time']

        return with_playlist + without_playlist
