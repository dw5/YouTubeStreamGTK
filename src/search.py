# search.py
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
        # for internal plugins only
        self.app_window = kwargs.get('app_window', None)
        self.spinner = kwargs.get('spinner', None)
        self.scroller = kwargs.get('scroller', None)

        self.si_index = 0
        self.this_instance = self.app_window.strong_instances[self.si_index]

        self.search_video_ids = []

        # limited access
        self.add_result_meta = kwargs.get('add_result_meta', None)

    def do_search(self, query, page):
        self.spinner.set_visible(True)
        self.query = query
        esc_query = GLib.uri_escape_string(self.query, None, None)
        uri = f"{self.this_instance}/api/v1/search?q={esc_query};page={page};fields=title,videoId,author,lengthSeconds,videoThumbnails"
        #print(uri)

        self.session = Soup.Session.new()
        self.session.set_property("timeout", 5)
        message = Soup.Message.new("GET", uri)
        self.session.queue_message(message, self.show_results, page)

    def show_results(self, session, results, page):
        if results.status_code != 200:
            if page == 1:
                self.app_window.show_error_box("Service Failure",
                    "There is no response from the streaming servers.")
            return False

        try:
            self.search_json = json.loads(results.response_body.data)
        except:
            if page == 1:
                self.app_window.show_error_box("Service Failure",
                    "The streaming server response failed to parse results.")
            return False

        for video_meta in self.search_json:
            if video_meta['videoId'] not in self.search_video_ids:
                self.get_poster_url(video_meta)
                self.get_video_details(video_meta)

    def get_poster_url(self, video_meta):
        for poster in video_meta['videoThumbnails']:
            if poster['quality'] == 'medium':
                if poster['url'].startswith('/'):
                    video_meta['poster_uri'] = f"{self.this_instance}{poster['url']}"
                else:
                    video_meta['poster_uri'] = poster['url']

    def get_video_details(self, video_meta):
        video_id = video_meta['videoId']
        uri = f"{self.this_instance}/api/v1/videos/{video_id}?fields=adaptiveFormats,formatStreams"
        self.session = Soup.Session.new()
        self.session.set_property("timeout", 5)
        message = Soup.Message.new("GET", uri)
        self.session.queue_message(message, self.parse_video_results, video_meta)

    def parse_video_results(self, session, results, video_meta):
        if results.status_code != 200:
            # remove unplayable video urls from list
            return False

        try:
            self.video_json = json.loads(results.response_body.data)
        except:
            return False

        video_meta['video_uri'] = None
        for format_stream in self.video_json['formatStreams']:

            if format_stream['qualityLabel'] == "360p":
                video_meta['video_uri'] = format_stream['url']

            # if (future) user-config desires 720p,
            # check if it is available and if so use it instead
            #if format_stream['qualityLabel'] == "720p":
            #    self.video_uri = format_stream['url']

        if not video_meta['video_uri']:
            return False

        self.check_video_playable(video_meta)
        self.get_download_uris(video_meta)

    def check_video_playable(self, video_meta):
        video_uri = video_meta['video_uri']
        session = Soup.Session.new()
        session.set_property("timeout", 2)
        message = Soup.Message.new("HEAD", video_uri)
        session.queue_message(message, self.check_video_playable_cb, video_meta)

    def check_video_playable_cb(self, session, results, video_meta):
        if results.status_code != 200:
            #print('Unplayable video file, trying next instance')
            #print(video_meta['title'])
            video_meta.pop('video_uri')
            self.si_index += 1
            if len(self.app_window.strong_instances) > self.si_index:
                self.this_instance = self.app_window.strong_instances[self.si_index]
                #print(self.this_instance)
                self.get_video_details(video_meta)
            else:
                #print("Out of instances, breaking")
                return False

        if 'video_uri' in video_meta:
            # add the result to the video meta
            # which will trigger the video to display to the user
            self.add_result_meta(video_meta)

            # appending known playable videos to filter duplicates
            self.search_video_ids.append(video_meta['videoId'])

            self.spinner.set_visible(False)
            self.scroller.set_visible(True)

    def get_download_uris(self, video_meta):
        # get download link urls based on (future) user-config
        # video quality: ["480p", "720p", "1080p"] # default 720p
        # audio structure:
        #     "bitrate": "142028",
        #     "type": "audio/webm; codecs=\"opus\"",
        #     "container": "webm",
        # video structure:
        #     "bitrate": "440700",
        #     "type": "video/mp4; codecs=\"avc1.4d401f\"",
        #     "container": "mp4",
        #     "qualityLabel": "720p"

        last_bitrate = None
        video_meta['audio_dl_uri'] = None
        for af in self.video_json['adaptiveFormats']:
            if af['type'].startswith('audio/mp4'):
                if not video_meta['audio_dl_uri']:
                    last_bitrate = af['bitrate']
                    video_meta['audio_dl_uri'] = af['url']

                if af['bitrate'] > last_bitrate:
                    last_bitrate = af['bitrate']
                    video_meta['audio_dl_uri'] = af['url']

        video_quality = "720p"
        video_meta['video_dl_uri'] = None
        for fs in self.video_json['formatStreams']:
            if fs['type'].startswith('video/mp4'):
                # set it to something
                if not video_meta['video_dl_uri']:
                    video_meta['video_dl_uri'] = fs['url']

                if 'qualityLabel' in fs:
                    if fs['qualityLabel'] == "720p" and video_quality == "720p":
                        video_meta['video_dl_uri'] = fs['url']
                    elif fs['qualityLabel'] == "480p" and video_quality == "480p":
                        video_meta['video_dl_uri'] = fs['url']
                    elif fs['qualityLabel'] == "1080p" and video_quality == "1080p":
                        video_meta['video_dl_uri'] = fs['url']
