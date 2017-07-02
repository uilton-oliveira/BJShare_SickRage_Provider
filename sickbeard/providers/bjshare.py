# coding=utf-8
# Author: Uilton de Oliveira (aka DarkSupremo) <contato@uiltonsites.com.br>
#
# URL: https://www.uiltonsites.com.br
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import re
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar
from requests.utils import add_dict_to_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BJShareProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def searchcut(self, source, startsearch, endsearch, startpos=0, includetag=False):
        start = 0

        def finalresult(result):
            if includetag:
                return startsearch + result + endsearch
            else:
                return result

        if startsearch:
            start = source.find(startsearch, startpos)
            if start == -1:
                return {"pos":-1, "pos_end":-1, "txt":""}
            start += len(startsearch)

        end = 0

        if endsearch:
            end = source.find(endsearch, start)

        if end == -1:
            return {"pos":-1, "pos_end":-1, "txt":""}

        if end == 0:
            return {"pos":start, "pos_end":end, "txt": finalresult(source[start:])}

        if start == 0:
            return {"pos":start, "pos_end":end, "txt": finalresult(source[:end])}

        return {"pos":start, "pos_end":end, "txt": finalresult(source[start:end])}

    def __init__(self):

       # Provider Init
        TorrentProvider.__init__(self, "BJShare")

        # URLs
        self.url = 'https://bj-share.me'
        self.urls = {
            'login': urljoin(self.url, "index.php"),
            'detail': urljoin(self.url, "torrents.php?id=%s"),
            'search': urljoin(self.url, "torrents.php"),
            'download': urljoin(self.url, "%s"),
        }

        # Credentials
        self.enable_cookies = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Proper Strings
        self.proper_strings = ["PROPER", "REPACK", "REAL"]

        # Cache
        self.cache = tvcache.TVCache(self, min_time=1)

        self.quality = {
            '1080p': 'Full HD',
            '720p': 'HD',
            'BR-Rip': 'BRRip',
            'DVD-Rip': 'DVDRip',
            'BR-Disk': 'Blu-ray',
            'TeleCine': 'HDTC'
        }

        self.quality_reverse = {}
        for key, value in self.quality.iteritems():
            self.quality_reverse[value] = key


    def _check_auth(self):
        if not self.cookies:
            logger.log(u"Invalid cookie session. Check your settings", logger.WARNING)

        return True

    def login(self):

        cookie_dict = dict_from_cookiejar(self.session.cookies)
        if cookie_dict.get('session'):
            return True

        if self.cookies:
            add_dict_to_cookiejar(self.session.cookies, dict(x.rsplit('=', 1) for x in self.cookies.split(';')))
            #undecoded_session = urllib.unquote(str(self.cookies))
            #encoded_session = urllib.quote(str(undecoded_session))
            #add_dict_to_cookiejar(self.session.cookies, {'session', encoded_session})

        cookie_dict = dict_from_cookiejar(self.session.cookies)
        if cookie_dict.get('session'):
            return True

        if self.cookies:
            success, status = self.add_cookies_from_ui()
            if not success:
                logger.log(status, logger.INFO)
                return False

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []
        if not self.login():
            return results

        anime = bool(ep_obj and ep_obj.show and ep_obj.show.anime)

        search_params = {
            "order_by": "time",
            "order_way": "desc",
            "group_results": 0,
            "action": "basic",
            "searchsubmit": 1
        }

        logger.log(ep_obj, logger.DEBUG)

        if anime:
            search_params["filter_cat[14]"] = 1
        else:
            search_params["filter_cat[2]"] = 1

        units = ["B", "KB", "MB", "GB", "TB", "PB"]

        def process_column_header(td):
            result = ""
            if td.a and td.a.img:
                result = td.a.img.get("title", td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        if anime:
            search_strings = {u"Episode": [ep_obj.show.name]}

        for mode in search_strings:
            items = []
            logger.log(u"Search Mode: {0}".format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log(u"Search string: {0}".format
                               (search_string.decode("utf-8")), logger.DEBUG)

                search_params['searchstr'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log("No data returned from provider", logger.DEBUG)
                    continue

                # logger.log(data, logger.DEBUG)


                with BS4Parser(data, "html5lib") as html:
                    torrent_table = html.find("table", id="torrent_table")
                    torrent_rows = torrent_table("tr") if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        logger.log("Data returned from provider does not contain any torrents", logger.DEBUG)
                        continue

                    # "", "", "Name /Year", "Files", "Time", "Size", "Snatches", "Seeders", "Leechers"
                    labels = [process_column_header(label) for label in torrent_rows[0]("td")]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        cells = result("td")
                        if len(cells) < len(labels):
                            continue

                        torrent = {}

                        try:
                            title = cells[labels.index("Nome/Ano")].find("a", dir="ltr").get_text(strip=True)
                            if '[' in title and ']' in title:
                                torrent['national_title'] = self.searchcut(title, '', ' [')
                                torrent['international_name'] = self.searchcut(title, '[', ' ]')
                            else:
                                torrent['international_name'] = title

                            year = cells[labels.index("Nome/Ano")].find("a", dir="ltr").next_sibling.strip().replace('[', '').replace(']', '')
                            torrent['year'] = year
                            download_url = urljoin(self.url, cells[labels.index("Nome/Ano")].find("a", title="Baixar")["href"])
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[labels.index("Seeders")].get_text(strip=True))
                            leechers = try_int(cells[labels.index("Leechers")].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != "RSS":
                                    logger.log("Discarding torrent because it doesn't meet the"
                                               " minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                               (title, seeders, leechers), logger.DEBUG)
                                continue

                            torrent_details = cells[labels.index("Nome/Ano")].find("div", attrs={"class": "torrent_info"}).get_text(strip=True).replace('[', '').replace(']', '')

                            torrent_details_slitted = torrent_details.split(' / ')
                            details = []
                            for torrent_detail in torrent_details_slitted:
                                detail = torrent_detail.strip()
                                details.append(detail)

                            resolution = ''
                            if len(details) >= 7 and details[6] != 'Free':
                                resolution = self.quality_reverse[details[6]]
                            else:
                                resolution = '480p'

                            source = details[3]
                            codec = details[2]
                            audio = details[4]
                            ext = details[0]

                            torrent_size = cells[labels.index("Tamanho")].get_text(strip=True)
                            size = convert_size(torrent_size, units=units) or -1
                            try:
                                season = re.findall(r"(?:s|season)(\d{2})", title, re.I)[0]
                            except IndexError:
                                season = ''

                            try:
                                episode = re.findall(r"(?:e|x|episode|ep|\n)(\d{2,4})", title, re.I)[0]
                            except IndexError:
                                episode = ''

                            if episode.isdigit():
                                title = title[:title.rfind('-')].strip()

                                torrent_name = u"{0} {1} {2} {3} {4} {5}-BJShare.{6}".format(title, episode, resolution,
                                                                                     source, codec, audio, ext)

                                if anime and int(episode) != ep_obj.absolute_number:

                                    logger.log("Found Torrent: {0} episode detected: {1} but was not the episode we was searching {2}, skipping.".format
                                               (torrent_name, int(episode), ep_obj.absolute_number), logger.DEBUG)
                                    continue
                                elif anime:
                                    logger.log("Found Torrent Match: {0}".format(torrent_name), logger.DEBUG)

                            elif season.isdigit:
                                title = title = title[:title.rfind('-')].strip()

                            if anime:
                                torrent_name = u"{0} {1} {2} {3} {4} {5}-BJShare.{6}".format(title, episode, resolution, source, codec, audio, ext)
                            else:
                                torrent_name = u"{0} ({1}) S{2}E{3} {4} {5} {6} {7}.{8}".format(title,
                                                                                       torrent['year'], season, episode,
                                                                                       resolution, source, codec, audio, ext)

                            item = {'title': torrent_name, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
                            if mode != "RSS":
                                logger.log("Found result: {0} with {1} seeders and {2} leechers".format
                                           (torrent_name, seeders, leechers), logger.DEBUG)

                            items.append(item)
                        except StandardError:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = BJShareProvider()
