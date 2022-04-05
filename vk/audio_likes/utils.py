def code_for_savers_count(owner_id: str or int, audio_id: str or int):
    code = 'var user_id = API.users.get()[0].id; ' \
           'var audio_id = API.audio.add({"owner_id": ' + str(owner_id) + ',' \
                                        '"audio_id": ' + str(audio_id) + '}); ' \
           'var savers_count = API.likes.delete({"type": "audio", ' \
                                                '"owner_id": ' + str(owner_id) + ', ' \
                                                '"item_id": ' + str(audio_id) + '}).likes; ' \
           'API.audio.delete({"owner_id": user_id, "audio_id": audio_id}); ' \
           'return savers_count;'
    return code
