import re

# from urllib.parse import parse_qs, urlparse

uri_playlist_regex = re.compile("^(?:tidaltube):playlist:(?P<playlistid>.+)$")


def format_playlist_uri(id) -> str:
    return f"tidaltube:playlist:{id}"


def extract_playlist_id(uri) -> str:
    match = uri_playlist_regex.match(uri)
    if match:
        return match.group("playlistid")
    return ""
