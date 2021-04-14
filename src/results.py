# results.py
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
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('Handy', '1')
gi.require_version('Soup', '2.4')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gst, Gtk, Handy, Soup

import json

Gst.init(None)
Gst.init_check(None)
Handy.init()

import time

@Gtk.Template(resource_path='/sm/puri/Stream/ui/results.ui')
class ResultsBox(Gtk.Box):
    __gtype_name__ = 'ResultsBox'

    event_box = Gtk.Template.Child()
    player_box = Gtk.Template.Child()
    poster_image = Gtk.Template.Child()
    controls_box = Gtk.Template.Child()
    play = Gtk.Template.Child()
    pause = Gtk.Template.Child()
    slider = Gtk.Template.Child()
    time_viewed = Gtk.Template.Child()
    time_remaining = Gtk.Template.Child()

    audio_dl = Gtk.Template.Child()
    audio_dl_image = Gtk.Template.Child()
    video_dl = Gtk.Template.Child()
    video_dl_image = Gtk.Template.Child()
    speed = Gtk.Template.Child()
    fullscreen = Gtk.Template.Child()
    unfullscreen = Gtk.Template.Child()

    details = Gtk.Template.Child()
    title = Gtk.Template.Child()
    channel = Gtk.Template.Child()
    duration = Gtk.Template.Child()

    window_to_player_box_padding = 28

    def __init__(self, app_window, priority_index, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window
        self.priority = 0
        if priority_index > 0:
            self.priority = GLib.PRIORITY_LOW

        # listen for motion on the player box for controls show/hide
        self.event_box.add_events(Gdk.EventMask.POINTER_MOTION_MASK)

        # determine window width at time of search
        # do ratio calculation from width (16:9 or 1.77)
        # retain aspect ratio
        size = self.app_window.get_size()
        self.app_orig_width = size.width
        self.app_orig_height = size.height
        self.video_box_width = int(size.width - self.window_to_player_box_padding)
        self.video_box_height = int(self.video_box_width / 1.77)

        self.player_box.set_size_request(self.video_box_width, self.video_box_height)
        self.poster_image.set_size_request(self.video_box_width, self.video_box_height)

        # init gstreamer player
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.sink = Gst.ElementFactory.make("gtksink")

        self.video_widget = self.sink.get_property("widget")
        self.video_widget.set_size_request(self.video_box_width, self.video_box_height)

        self.player_box.add(self.video_widget)

    def get_readable_seconds(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if seconds >= 3600:
            readable_seconds = f"{h:d}:{m:02d}:{s:02d}"
        else:
            readable_seconds = f"{m:d}:{s:02d}"
        return readable_seconds

    def on_file_read(self, poster_file, async_res, user_data):
        try:
            stream = poster_file.read_finish(async_res)
        except GLib.Error as e:
            return False

        GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(stream,
                self.video_box_width, self.video_box_height,
                True,                # preserve_aspect_ratio
                None,                # cancellable
                self.on_stream_load, # callback
                None)                # user_data

    def on_stream_load(self, source, async_res, context):
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(async_res)

        self.poster_image.clear()
        self.poster_image.set_from_pixbuf(pixbuf)

    def stream_at_scale_async(self, poster_file):
        stream = poster_file.read_async(self.priority, None,
                self.on_file_read, None)

    def check_video_playable(self, video_url):
        session = Soup.Session.new()
        session.set_property("timeout", 2)
        message = Soup.Message.new("HEAD", video_url)
        session.queue_message(message, self.check_video_playable_cb, None)

    def check_video_playable_cb(self, session, results, user_data):
        if results.status_code != 200:
            self.set_visible(False)

    def parse_video_results(self, session, result, message):
        if message.status_code != 200:
            # remove unplayable video urls from list
            self.set_visible(False)
            return False

        try:
            self.json = json.loads(message.response_body.data)
        except:
            self.set_visible(False)
            return False

        self.video_uri = None
        for format_stream in self.json['formatStreams']:

            if format_stream['qualityLabel'] == "360p":
                self.video_uri = format_stream['url']

            # if (future) user-config desires 720p,
            # check if it is available and if so use it instead
            #if format_stream['qualityLabel'] == "720p":
            #    self.video_uri = format_stream['url']

        if not self.video_uri:
            self.set_visible(False)
            return False

        self.check_video_playable(self.video_uri)

        self.get_download_uris()

        self.player.set_property("uri", self.video_uri)
        self.player.set_property("video-sink", self.sink)

        poster_file = Gio.File.new_for_uri(self.poster_uri)

        self.stream_at_scale_async(poster_file)

    def get_video_details(self):
        uri = f"{self.instance}/api/v1/videos/{self.video_id}?fields=adaptiveFormats,formatStreams"
        self.session = Soup.Session.new()
        self.session.set_property("timeout", 5)
        message = Soup.Message.new("GET", uri)
        self.session.queue_message(message, self.parse_video_results, message)

    def setup_stream(self, video_meta):
        self.instance = video_meta['strong_instance']
        self.video_id = video_meta['videoId']
        self.video_title = video_meta['title']
        self.video_channel = video_meta['author']
        self.poster_uri = video_meta['poster_uri']
        video_duration = self.get_readable_seconds(video_meta['lengthSeconds'])

        self.title.set_label(self.video_title)
        self.channel.set_label(self.video_channel)
        self.duration.set_label(video_duration)

        self.get_video_details()

    def update_slider(self):
        if not self.app_window.is_playing:
            return False
        else:
            success, duration = self.player.query_duration(Gst.Format.TIME)

            # GtkScale is set to 100%, calculate duration and position steps
            self.percent = 100 / (duration / Gst.SECOND)

            # get current position (nanoseconds)
            success, position = self.player.query_position(Gst.Format.TIME)

            position_value = float(position) / Gst.SECOND * self.percent

            if int(duration) > 0:
                viewed_seconds = int(position / Gst.SECOND)
                remaining_seconds = int((duration - position) / Gst.SECOND)
                viewed = self.get_readable_seconds(viewed_seconds)
                remaining = self.get_readable_seconds(remaining_seconds)

                self.time_viewed.set_label(viewed)
                self.time_remaining.set_label(f"-{remaining}")

            # is negative number when not successful, so put it to 0
            if not success:
                position_value = 0
            
            try:
                # block seek slider function so it doesn't loop itself
                self.slider.handler_block_by_func(self.seek_slider)
                self.slider.set_value(position_value)
                self.slider.handler_unblock_by_func(self.seek_slider)
            except:
                return False

        return True

    def strictify_name(self, s):
        return "".join( x for x in s if (x.isalnum() or x in "_- "))

    def download_audio_uri(self, uri):
        dl_stream = Gio.File.new_for_uri(uri)
        dest_ext = "m4a"
        try:
            dest_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
        except:
            self.show_error_icon('audio')
            return False

        dest_title = self.strictify_name(self.video_title)
        dest_path = f"{dest_dir}/{dest_title}.{dest_ext}"
        dest = Gio.File.new_for_path(dest_path)
        dl_stream.copy_async(dest, Gio.FileCopyFlags.OVERWRITE,
                GLib.PRIORITY_LOW, None,
                self.progress_audio_cb, (),
                self.ready_audio_cb, None)

    def download_video_uri(self, uri):
        dl_stream = Gio.File.new_for_uri(uri)
        dest_ext = "mp4"
        try:
            dest_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
        except:
            self.show_error_icon('video')
            return False

        dest_title = self.strictify_name(self.video_title)
        dest_path = f"{dest_dir}/{dest_title}.{dest_ext}"
        dest = Gio.File.new_for_path(dest_path)
        flags = Gio.FileCopyFlags
        dl_stream.copy_async(dest,
                # bitwise or (not tuple) for multiple flags
                Gio.FileCopyFlags.OVERWRITE|Gio.FileCopyFlags.ALL_METADATA|Gio.FileCopyFlags.TARGET_DEFAULT_PERMS,
                GLib.PRIORITY_LOW, None,
                self.progress_video_cb, (),
                self.ready_video_cb, None)

    def show_success_icon(self, button):
        if button == 'audio':
            self.audio_dl_image.set_property('icon-name', 'object-select-symbolic')
        elif button == 'video':
            self.video_dl_image.set_property('icon-name', 'object-select-symbolic')

    def show_progress_icon(self, button):
        # could show progress in icon
        if button == 'audio':
            self.audio_dl_image.set_property('icon-name', 'document-save-as-symbolic')
        elif button == 'video':
            self.video_dl_image.set_property('icon-name', 'document-save-as-symbolic')

    def show_error_icon(self, button):
        if button == 'audio':
            self.audio_dl_image.set_property('icon-name', 'dialog-error-symbolic')
        elif button == 'video':
            self.video_dl_image.set_property('icon-name', 'dialog-error-symbolic')

    def progress_audio_cb(self, current_num_bytes, total_num_bytes, *user_data):
        percentage = round(current_num_bytes / total_num_bytes * 100)
        #print(f"Audio Downloading: {percentage}%", end="\r")

    def progress_video_cb(self, current_num_bytes, total_num_bytes, *user_data):
        percentage = round(current_num_bytes / total_num_bytes * 100)

    def ready_audio_cb(self, src, async_res, user_data):
        try:
            src.copy_finish(async_res)
        except GLib.Error as e:
            self.show_error_icon('audio')
            return False
        self.show_success_icon('audio')

    def ready_video_cb(self, src, async_res, user_data):
        try:
            src.copy_finish(async_res)
        except GLib.Error as e:
            self.show_error_icon('video')
            return False
        self.show_success_icon('video')

    @Gtk.Template.Callback()
    def audio_dl_button(self, button):
        self.audio_dl.set_sensitive(False)
        self.show_progress_icon('audio')
        self.download_audio_uri(self.audio_dl_uri)

    @Gtk.Template.Callback()
    def video_dl_button(self, button):
        self.video_dl.set_sensitive(False)
        self.show_progress_icon('video')
        self.download_video_uri(self.video_dl_uri)

    @Gtk.Template.Callback()
    def play_button(self, button):
        # loop through all child results pausing them
        self.app_window.pause_all()

        self.play.set_visible(False)
        self.pause.set_visible(True)
        self.player.set_state(Gst.State.PLAYING)
        self.app_window.is_playing = True

        # hide the poster, show the video
        self.player_box.show_all()
        self.poster_image.hide()

        # initialize the slider
        self.update_slider()
        # allow seeking
        self.slider.set_sensitive(True)

        # update slider to track video time in slider
        GLib.timeout_add_seconds(1, self.update_slider)

    @Gtk.Template.Callback()
    def pause_button(self, button):
        self.play.set_visible(True)
        self.pause.set_visible(False)
        self.player.set_state(Gst.State.PAUSED)
        self.app_window.is_playing = False

    @Gtk.Template.Callback()
    def speed_button(self, button):
        print("speed_button")

    def resize_player(self, width, height):
        self.poster_image.set_size_request(width, height)
        self.video_widget.set_size_request(width, height)

    @Gtk.Template.Callback()
    def fullscreen_button(self, button):
        self.fullscreen.set_visible(False)
        self.unfullscreen.set_visible(True)
        self.app_window.fullscreen()
        self.app_window.is_fullscreen = True
        self.app_window.search_bar_toggle.set_active(False)
        self.app_window.search_bar.set_visible(False)
        self.app_window.header_bar.set_visible(False)
        self.details.set_visible(False)

        set_width = int(Gdk.Screen.get_default().get_width())
        set_height = int(Gdk.Screen.get_default().get_height())
        self.resize_player(set_width, set_height)

        results_context = self.get_style_context()
        results_context.remove_class("results")
        results_context.add_class("fullscreen")

        # horizonal scrollbar, vertical scrollbar (do last)
        scroller = self.app_window.scroller_stack.get_visible_child()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)

        self.grab_focus()

    @Gtk.Template.Callback()
    def unfullscreen_button(self, button):
        self.fullscreen.set_visible(True)
        self.unfullscreen.set_visible(False)
        self.app_window.unfullscreen()
        self.app_window.is_fullscreen = False
        self.app_window.search_bar_toggle.set_active(True)
        self.app_window.search_bar.set_visible(True)
        self.app_window.header_bar.set_visible(True)
        self.details.set_visible(True)

        results_context = self.get_style_context()
        results_context.remove_class("fullscreen")
        results_context.add_class("results")

        set_width = int(self.app_orig_width - self.window_to_player_box_padding)
        set_height = int(set_width / 1.77)

        self.resize_player(set_width, set_height)
        self.app_window.resize(self.app_orig_width, self.app_orig_height)

        scroller = self.app_window.scroller_stack.get_visible_child()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.grab_focus()

    @Gtk.Template.Callback()
    def seek_slider(self, scale):
        seek = scale.get_value()

        # allow seeking when playing
        self.player.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek * Gst.SECOND / self.percent)

    def poll_mouse(self):
        now_is = int(GLib.get_current_time())
        if (int(now_is) - (self.last_move)) >= 1:
            if self.controls_box.get_visible():
                self.controls_box.set_visible(False)

    @Gtk.Template.Callback()
    def event_box_mouse_click(self, event, data):
        if self.app_window.is_playing:
            self.pause_button(None)
        self.event_box_mouse_action(event, data)

    @Gtk.Template.Callback()
    def event_box_mouse_action(self, event, data):
        self.last_move = int(GLib.get_current_time())
        GLib.timeout_add_seconds(2, self.poll_mouse)
        if not self.controls_box.get_visible():
            self.controls_box.set_visible(True)

    @Gtk.Template.Callback()
    def swallow_slider_scroll_event(self, event, data):
        return True

    def get_download_uris(self):
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
        self.audio_dl_uri = None
        for af in self.json['adaptiveFormats']:
            if af['type'].startswith('audio/mp4'):
                if not self.audio_dl_uri:
                    last_bitrate = af['bitrate']
                    self.audio_dl_uri = af['url']

                if af['bitrate'] > last_bitrate:
                    last_bitrate = af['bitrate']
                    self.audio_dl_uri = af['url']

        video_quality = "720p"
        self.video_dl_uri = None
        for fs in self.json['formatStreams']:
            if fs['type'].startswith('video/mp4'):
                # set it to something
                if not self.video_dl_uri:
                    self.video_dl_uri = fs['url']

                if 'qualityLabel' in fs:
                    if fs['qualityLabel'] == "720p" and video_quality == "720p":
                        self.video_dl_uri = fs['url']
                    elif fs['qualityLabel'] == "480p" and video_quality == "480p":
                        self.video_dl_uri = fs['url']
                    elif fs['qualityLabel'] == "1080p" and video_quality == "1080p":
                        self.video_dl_uri = fs['url']

        if self.audio_dl_uri:
            self.audio_dl.set_sensitive(True)

        if self.video_dl_uri:
            self.video_dl.set_sensitive(True)
