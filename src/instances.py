# instances.py
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
from gi.repository import Soup

import json

class Instances:

    def __init__(self, **kwargs):
        self.app_window = kwargs.get('app_window', None)

    def get_strong_instances(self):
        # this processes a series of tests
        # 1. check if instance api and search are valid
        # 2. check if the instance returns a valid video page result
        # 3. check if the instance returns valid video url
        # then sets it as a strong instance

        # get urls of instances from api.invidious.io
        uri = f"https://api.invidious.io/instances.json?sort_by=health"

        session = Soup.Session.new()
        session.set_property("timeout", 10)
        message = Soup.Message.new("GET", uri)
        session.queue_message(message, self.get_strong_instances_cb, None)

    def get_strong_instances_cb(self, session, results, user_data):
        if results.status_code != 200:
            self.app_window.show_error_box("Service Failure",
                    "No instances found, cannot complete search.")
            return False

        try:
            instances_json = json.loads(results.response_body.data)
        except:
            self.app_window.show_error_box("Service Failure",
                    "Instances are malformed, cannot complete search.")
            return False

        for instance in instances_json:
            instance_uri = instance[1]['uri'].rstrip('/')

            # remove non http gettable urls
            if (not instance_uri.endswith('.onion') and
                    not instance_uri.endswith('.i2p')):
                self.check_query_api_valid(instance[1]['uri'])

        # add a backup
        self.check_query_api_valid('https://iteroni.com')

    # check the instance can run a query on the API
    def check_query_api_valid(self, uri):
        # /api/v1/search?q=query
        # /api/v1/search?q=Librem%205;fields=type
        search_uri = f"{uri}/api/v1/search?q=Librem%205;fields=type"
        session = Soup.Session.new()
        session.set_property("timeout", 2)
        message = Soup.Message.new("GET", search_uri)
        session.queue_message(message, self.check_query_valid_cb, uri)

    def check_query_valid_cb(self, session, results, uri):
        if results.status_code != 200:
            return False

        try:
            instance_json = json.loads(results.response_body.data)
        except:
            return False

        # only need to check if 'type' appears
        for r in instance_json:
            if 'type' in r:
                self.check_video_api_valid(uri)
                break

    # check the instances return a valid API
    def check_video_api_valid(self, uri):
        # api urls to confirm are strong (some throw forbidden)
        # /api/v1/videos/{videoId}
        # /api/v1/videos/cAUNrY_qPCg?fields=type
        fs_uri = f"{uri}/api/v1/videos/cAUNrY_qPCg?fields=formatStreams"
        session = Soup.Session.new()
        session.set_property("timeout", 2)
        message = Soup.Message.new("GET", fs_uri)
        session.queue_message(message, self.check_video_api_valid_cb, uri)

    def check_video_api_valid_cb(self, session, results, uri):
        if results.status_code != 200:
            return False

        try:
            instance_json = json.loads(results.response_body.data)
        except:
            return False

        # verify json has key 'formatStreams' (not 'error')
        if 'formatStreams' in instance_json:
            fs = instance_json['formatStreams'][0]
            if fs['type'].startswith('video/mp4'):
                confirm_video = fs['url']
                self.check_video_valid(uri, confirm_video)

    def check_video_valid(self, uri, confirm_video):
        session = Soup.Session.new()
        session.set_property("timeout", 2)
        message = Soup.Message.new("HEAD", confirm_video)
        session.queue_message(message, self.check_video_valid_cb, uri)

    def check_video_valid_cb(self, session, results, uri):
        if results.status_code != 200:
            return False

        self.app_window.strong_instances.append(uri)
        self.app_window.status_icon.set_property('icon-name', 'object-select-symbolic')
