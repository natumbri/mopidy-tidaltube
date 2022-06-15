import re
from concurrent.futures.thread import ThreadPoolExecutor

# from mopidy_youtube.comms import Client
import requests
from bs4 import BeautifulSoup as bs

from mopidy_tidaltube import logger
from mopidy_tidaltube.yt_provider import search_and_get_best_match


class Tidal:
    def _get_tidal_soup(url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.1) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/80.0.3987.149 Safari/537.36"
            )
        }
        page = requests.get(url, headers=headers)
        fixed_page = page.text.replace(" */", " */ \n")
        soup = bs(fixed_page, "html5lib")
        return soup

    @classmethod
    def get_tidal_user_playlists(cls, playlists):
        pass

    @classmethod
    def get_tidal_playlist_details(cls, playlists):
        def job(playlist):
            soup = cls._get_tidal_soup(
                f"https://tidal.com/browse/playlist/{playlist}"
            )
            playlist_name = soup.find("title").text
            return {"name": playlist_name, "id": playlist}

        results = []

        # tidal uses a captcha, so hitting this hard will break it
        with ThreadPoolExecutor(1) as executor:
            futures = executor.map(job, playlists)
            [results.append(value) for value in futures if value is not None]

        return results

    @classmethod
    def get_tidal_playlist_tracks(cls, playlist):
        # get tracks for each playlist and translate to ytm
        soup = cls._get_tidal_soup(
            f"https://tidal.com/browse/playlist/{playlist}"
        )
        tracks_soup = soup.find_all("div", class_="track-item has-info")
        track_dict = {}
        for index, track in enumerate(tracks_soup):
            song_name = (
                track.select('div[class*="track-name"]')[0]
                .a.contents[0]
                .strip()
            )
            song_artists = [
                track.select('div[class*="track-artists"]')[0]
                .a.contents[0]
                .strip()
            ]

            # albumTitle is not used; could use it for cross-checking with track_dict2
            # would also be nice to send it to mopidy-youtube, somehow, since it isn't
            # looked up when the [Ref.track] is returned by the Library backend
            # albumTitle = (
            #     track.select('div[class*="track-info"]')[0].a.contents[0].strip()
            # )

            # is there any way to get isrc from tidal?
            # isrc = ???

            track_dict[index] = {
                "song_name": song_name,
                "song_artists": song_artists,
                "isrc": None,
            }

        track_script = soup.find("script", {"data-n-head": None}).text

        track_pattern = re.compile(
            r"[a-zA-Z]\[(?P<track>\d+)\]=(?P<data>[^;]+)"
        )

        track_info_pattern = re.compile(
            r"albumID\:(?P<albumId>[^,]+).*"
            r'albumTitle\:"?(?P<albumTitle>[^,"]+).*'
            r"artists\:\[\{id\:(?P<artistId>[^,]+),"
            r'name\:"?(?P<artistName>[^"\}]+).*'
            r"duration\:(?P<duration>[^,]+).*"
            r'title\:"?(?P<trackTitle>[^,"]+)'
        )

        matches = track_pattern.finditer(track_script)
        if matches:
            track_dict2 = {
                match["track"]: track_info_pattern.search(
                    match["data"]
                ).groupdict()
                for match in matches
            }

        if track_dict2 and len(track_dict) == len(track_dict2):
            for track in track_dict:
                if "duration" in track_dict2[str(track)]:
                    try:
                        track_dict[track]["song_duration"] = int(
                            track_dict2[str(track)]["duration"]
                        )
                    except ValueError:
                        track_dict[track]["song_duration"] = None
                else:
                    track_dict[track]["song_duration"] = None
        else:
            logger.warn("track_dict length mismatch")

        tracks = list(track_dict.values())

        # search_and_get_best_match is slow, so with multithreading
        # but have to use a wrapper to pass a dict
        def search_and_get_best_match_wrapper(track):
            track.update({"id": search_and_get_best_match(**track)})
            return track

        results = []

        with ThreadPoolExecutor(4) as executor:
            futures = executor.map(search_and_get_best_match_wrapper, tracks)
            [results.append(value) for value in futures if value is not None]

        return results
