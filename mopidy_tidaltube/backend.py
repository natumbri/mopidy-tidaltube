import json

import pykka
from cachetools import TTLCache, cached
from mopidy import backend
from mopidy.models import Ref

from mopidy_tidaltube import Extension, logger
from mopidy_tidaltube.data import extract_playlist_id
from mopidy_tidaltube.tidal import Tidal


class TidalTubeBackend(pykka.ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super().__init__()
        self.config = config
        self.library = TidalTubeLibraryProvider(backend=self)
        self.tidal_playlists = config["tidaltube"]["tidal_playlists"]
        self.uri_schemes = ["tidaltube"]
        self.user_agent = "{}/{}".format(Extension.dist_name, Extension.version)

    def on_start(self):
        # proxy = httpclient.format_proxy(self.config["proxy"])
        # headers = {
        #     "user-agent": httpclient.format_user_agent(self.user_agent),
        #     "Cookie": "PREF=hl=en; CONSENT=YES+20210329;",
        #     "Accept-Language": "en;q=0.8",
        # }
        self.library.tidal = Tidal()


class TidalTubeLibraryProvider(backend.LibraryProvider):

    """
    Called when root_directory is set to [insert description]
    When enabled makes possible to browse the playlists listed in config
    ["tidaltube"]["tidal_playlists"] and the separate tracks those playlists.
    """

    root_directory = Ref.directory(uri="tidaltube:browse", name="TidalTube")

    cache_max_len = 4000
    cache_ttl = 21600

    tidal_cache = TTLCache(maxsize=cache_max_len, ttl=cache_ttl)

    @cached(cache=tidal_cache)
    def browse(self, uri):
        # if we're browsing, return a list of directories
        if uri == "tidaltube:browse":
            return [
                Ref.directory(
                    uri="tidaltube:playlist:root", name="Tidal Playlists"
                ),
            ]

        # if we're looking at playlists, return a list of the playlists
        # as directories: extract names and uris, return a list of Refs
        if uri == "tidaltube:playlist:root":
            playlistrefs = []
            playlists = self.tidal.get_tidal_playlist_details(
                self.backend.tidal_playlists
            )
            playlistrefs = [
                Ref.directory(
                    uri=f"tidaltube:playlist:{playlist['id']}",
                    name=playlist["name"],
                )
                for playlist in playlists
                if playlist["id"]
            ]
            return playlistrefs

        # if we're looking at a tidal playlist, return a list of tracks
        elif extract_playlist_id(uri):
            logger.debug(f"browse tidal playlist {uri}")
            trackrefs = []
            tracks = self.tidal.get_tidal_playlist_tracks(
                extract_playlist_id(uri)
            )
            trackrefs = [
                Ref.track(
                    uri=f"yt:video:{track['videoId']}",
                    name=track["title"],
                )
                for track in tracks
                if "videoId" in track
            ]
            trackrefs[0] = Ref.track(
                uri=(
                    f"yt:video:{tracks[0]['videoId']}"
                    f":preload:"
                    f"{json.dumps([track for track in tracks if track is not None])}"
                ),
                name=tracks[0]["title"],
            )
            return trackrefs
