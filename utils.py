try:
    import simplejson as json
except ImportError:
    import json


def json_iter_parse(response_text):
    decoder = json.JSONDecoder(strict=False)
    idx = 0
    while idx < len(response_text):
        obj, idx = decoder.raw_decode(response_text, idx)
        yield obj


def remove_meaningless_args(args_dict):
    meaningful_items = filter(
        lambda item: not (item[1] is None or item[1] is False),
        args_dict.items()
    )
    return dict(meaningful_items)


def split_key_value(kv_pair):
    kv = kv_pair.split("=")
    return kv[0], kv[1]