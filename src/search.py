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
from gi.repository import Gio, GLib

from socket import timeout
from urllib.parse import urlencode
import urllib.request
import json

from .results import ResultsBox

class Search:

    def __init__(self, **kwargs):
        self.app_window = kwargs.get('app_window', None)
        self.query = kwargs.get('query', None)

        self.headers = ({
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome"
            "/75.0.3770.100 Safari/537.36"
        })

        search_task = Gio.Task.new(None, None, self.show_results, None)
        search_task.run_in_thread(self.do_search)

    def get_strong_instance(self):
        # lookup instances, get a strong one, to be done (stubbed for now)
        self.instance = "https://invidious.xyz"

    def clear_entries(self):
        children = self.app_window.results_list.get_children()
        for child in children:
            child.destroy()

    def do_search(self, task, source_obj, task_data, cancellable):
        self.json = {}
        self.get_strong_instance()

        enc_query = urlencode({'q': self.query})
        uri = f"{self.instance}/api/v1/search?{enc_query}"

        url = urllib.request.Request(uri, headers=self.headers)

        try:
            results = urllib.request.urlopen(url, timeout=5)
        except (urllib.error.HTTPError, timeout):
            print("URL did not respond")

        try:
            self.json = json.loads(results.read())
        except UnboundLocalError:
            print("json did not load from url results")

        self.get_poster_url()

    def show_results(self, source_obj, task_data, cancellable):
        self.clear_entries()

        for video_meta in self.json:
            results_box = ResultsBox(self.app_window)
            self.app_window.results_list.add(results_box)

            results_box.setup_stream(video_meta)

        self.app_window.spinner.set_visible(False)
        self.app_window.results_window.set_visible(True)

    def get_poster_url(self):
        # tweak json with local poster url
        for video_meta in self.json:
            for poster in video_meta['videoThumbnails']:
                if poster['quality'] == 'medium':
                    video_meta['poster_uri'] = poster['url']
