# search.py
#
# Copyright 2021 Todd Weaver
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
gi.require_version('Gio', '2.0')
gi.require_version('Soup', '2.4')
from gi.repository import Gio, GLib, Soup

import json

from .results import ResultsBox

class Search:

    def __init__(self, **kwargs):
        self.app_window = kwargs.get('app_window', None)
        self.query = kwargs.get('query', None)

        self.do_search()

    def get_strong_instance(self):
        # lookup instances, get a strong one, to be done (stubbed for now)
        self.instance = "https://invidious.xyz"

    def clear_entries(self):
        children = self.app_window.results_list.get_children()
        for child in children:
            child.destroy()

    def do_search(self):
        self.get_strong_instance()

        query = GLib.uri_escape_string(self.query, None, None)
        uri = f"{self.instance}/api/v1/search?q={query};fields=title,videoId,author,lengthSeconds,videoThumbnails"

        self.session = Soup.Session.new()
        self.session.set_property("timeout", 5)
        message = Soup.Message.new("GET", uri)
        self.session.queue_message(message, self.show_results, message)

    def show_error_box(self, heading, text):
        self.app_window.error_box.set_visible(True)
        self.app_window.error_heading.set_label(heading)
        self.app_window.error_text.set_label(text)

    def show_results(self, session, result, message):
        self.clear_entries()
        self.app_window.spinner.set_visible(False)

        if message.status_code != 200:
            self.show_error_box("Service Failure",
                "There is no response from the streaming servers.")
            return False

        try:
            self.json = json.loads(message.response_body.data)
        except:
            self.show_error_box("Service Failure",
                "The streaming server response failed to parse results.")
            print("json did not load from url results")
            return False

        self.get_poster_url()

        for video_meta in self.json:
            results_box = ResultsBox(self.app_window)
            self.app_window.results_list.add(results_box)

            results_box.setup_stream(video_meta)

        self.app_window.results_window.set_visible(True)

    def get_poster_url(self):
        # tweak json with local poster url
        for video_meta in self.json:
            for poster in video_meta['videoThumbnails']:
                if poster['quality'] == 'medium':
                    video_meta['poster_uri'] = poster['url']
