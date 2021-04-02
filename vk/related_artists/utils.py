

def find_related_block_id(blocks):
    for block in blocks:
        if 'url' in block.keys() and 'related' in block['url']:
            return block['id']


def code_for_get_artist_cards_from_urls(urls_list):
    if len(urls_list) > 25:
        urls_list = urls_list[:25]

    code = 'return ['
    for url in urls_list:
        code += 'API.catalog.getAudioArtist({url: "' + url + '", need_blocks: 1}), '
    code = code[:-2]
    code += '];'

    return code
