# iteroni.py
#
# Copyright 2021 Purism, SPC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version('Soup', '2.4')
from gi.repository import GLib, Soup

import json

class Search:

    def __init__(self, **kwargs):
        self.add_result = kwargs.get('add_result', None)
        self.set_headerbar_color = kwargs.get('set_headerbar_color', None)
        self.hide_scroller_error_box = kwargs.get('hide_scroller_error_box', None)
        self.show_scroller_error_box = kwargs.get('show_scroller_error_box', None)

    def do_search(self, query):
        esc_query = GLib.uri_escape_string(query, None, None)
        self.this_instance = 'https://iteroni.com'
        uri = f"{self.this_instance}/api/v1/search?q={esc_query};fields=title,videoId,author,lengthSeconds,videoThumbnails"

        self.session = Soup.Session.new()
        self.session.set_property("timeout", 5)
        message = Soup.Message.new("GET", uri)
        self.session.queue_message(message, self.show_results, message)

    def show_results(self, session, result, message):
        if message.status_code != 200:
            self.show_scroller_error_box("Service Failure",
                "There is no response from the this server.")
            return False

        try:
            self.json = json.loads(message.response_body.data)
        except:
            self.show_scroller_error_box("Service Failure",
                "This server response failed to parse results.")
            return False

        self.hide_scroller_error_box()

        self.get_poster_url()

        for video_meta in self.json:
            self.add_result(video_meta)

        self.set_headerbar_color()

    def get_poster_url(self):
        # tweak json with local poster url
        for video_meta in self.json:
            # append the strong instance for results to use
            video_meta['strong_instance'] = self.this_instance
            for poster in video_meta['videoThumbnails']:
                if poster['quality'] == 'medium':
                    if poster['url'].startswith('/'):
                        video_meta['poster_uri'] = f"{self.this_instance}{poster['url']}"
                    else:
                        video_meta['poster_uri'] = poster['url']
