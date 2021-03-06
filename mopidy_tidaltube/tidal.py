import re

from bs4 import BeautifulSoup as bs
from mopidy_youtube.yt_matcher import search_and_get_best_match

from mopidy_tidaltube import logger


class Tidal:
    def _get_tidal_soup(self, url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.1) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/80.0.3987.149 Safari/537.36"
            )
        }
        page = self.session.get(url, headers=headers, timeout=20)
        fixed_page = page.text.replace(" */", " */ \n")
        soup = bs(fixed_page, "html5lib")
        return soup

    def get_tidal_user_playlists(self, playlists):
        pass

    def get_tidal_playlist_details(self, playlists):
        def job(playlist):
            soup = self._get_tidal_soup(
                f"https://tidal.com/browse/playlist/{playlist}"
            )
            playlist_name = soup.find("title").text
            return {"name": playlist_name, "id": playlist}

        results = []

        # tidal uses a captcha, so hitting this hard will break it
        [results.append(job(playlist)) for playlist in playlists]

        return results

    def get_tidal_playlist_tracks(self, playlist):
        # get tracks for each playlist and translate to ytm
        soup = self._get_tidal_soup(
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

        return search_and_get_best_match(tracks)
