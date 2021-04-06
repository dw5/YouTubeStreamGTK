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
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gst, Gtk, Handy

Gst.init()
Gst.init_check()
Handy.init()

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

    audio_dl = Gtk.Template.Child()
    video_dl = Gtk.Template.Child()
    speed = Gtk.Template.Child()
    fullscreen = Gtk.Template.Child()
    unfullscreen = Gtk.Template.Child()

    details = Gtk.Template.Child()
    title = Gtk.Template.Child()
    channel = Gtk.Template.Child()
    duration = Gtk.Template.Child()

    window_to_player_box_padding = 28

    def __init__(self, app_window, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window

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

        # init gstreamer player
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.sink = Gst.ElementFactory.make("gtksink")

        self.video_widget = self.sink.get_property("widget")
        self.video_widget.set_size_request(self.video_box_width, self.video_box_height)

        self.player_box.add(self.video_widget)

    def get_duration(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if seconds >= 3600:
            self.video_duration = f"{h:d}:{m:02d}:{s:02d}"
        else:
            self.video_duration = f"{m:d}:{s:02d}"

    def on_file_read(self, poster_file, async_res, user_data):
        stream = poster_file.read_finish(async_res)
        GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(stream,
                                                    self.video_box_width, self.video_box_height,
                                                    True,           # preserve_aspect_ratio
                                                    None,           # cancellable
                                                    self.on_stream_load, # callback
                                                    None)           # user_data

    def on_stream_load(self, source, async_res, context):
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(async_res)

        self.poster_image.clear()
        self.poster_image.set_from_pixbuf(pixbuf)

    def stream_at_scale_async(self, poster_file):
        stream = poster_file.read_async(GLib.PRIORITY_DEFAULT, None, self.on_file_read, None)

    def setup_stream(self, video_meta):
        video_title = video_meta['title']
        video_channel = video_meta['author']
        video_id = video_meta['videoId']
        poster_uri = video_meta['poster_uri']
        self.get_duration(video_meta['lengthSeconds'])

        self.title.set_label(video_title)
        self.channel.set_label(video_channel)
        self.duration.set_label(self.video_duration)

        uri = f"http://iteroni.com/latest_version?id={video_id}&itag=18"

        # this should be done on play button press
        self.player.set_property("uri", uri)
        self.player.set_property("video-sink", self.sink)

        poster_file = Gio.File.new_for_uri(poster_uri)

        self.stream_at_scale_async(poster_file)

    def update_slider(self):
        if not self.is_playing:
            return False
        else:
            success, self.duration = self.player.query_duration(Gst.Format.TIME)

            # GtkScale is set to 100%, calculate duration and position steps
            self.percent = 100 / (self.duration / Gst.SECOND)

            # get current position (nanoseconds)
            success, position = self.player.query_position(Gst.Format.TIME)

            position_value = float(position) / Gst.SECOND * self.percent

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

    @Gtk.Template.Callback()
    def audio_dl_button(self, button):
        print("audio_dl_button")

    @Gtk.Template.Callback()
    def video_dl_button(self, button):
        print("video_dl_button")

    @Gtk.Template.Callback()
    def play_button(self, button):
        self.play.set_visible(False)
        self.pause.set_visible(True)
        self.player.set_state(Gst.State.PLAYING)
        self.is_playing = True

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
        self.is_playing = False

    @Gtk.Template.Callback()
    def speed_button(self, button):
        print("speed_button")

    def resize_player(self, width, height):
        self.poster_image.set_size_request(width, height)
        self.video_widget.set_size_request(width, height)

    def visible_children(self, visible, child_to_match):
        children = self.app_window.results_list.get_children()
        for child in children:
            if child == child_to_match:
                child.set_visible(True)
            else:
                child.set_visible(visible)

    @Gtk.Template.Callback()
    def fullscreen_button(self, button):
        self.fullscreen.set_visible(False)
        self.unfullscreen.set_visible(True)
        self.app_window.fullscreen()
        self.app_window.search_bar_toggle.set_active(False)
        self.app_window.search_bar.set_visible(False)
        self.app_window.header_bar.set_visible(False)
        self.visible_children(False, self.get_parent())
        self.details.set_visible(False)

        set_width = int(Gdk.Screen.get_default().get_width())
        set_height = int(Gdk.Screen.get_default().get_height())
        self.resize_player(set_width, set_height)
        self.app_window.results_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)

        results_context = self.get_style_context()
        results_context.remove_class("results")
        results_context.add_class("fullscreen")

    @Gtk.Template.Callback()
    def unfullscreen_button(self, button):
        self.fullscreen.set_visible(True)
        self.unfullscreen.set_visible(False)
        self.app_window.unfullscreen()
        self.app_window.search_bar_toggle.set_active(True)
        self.app_window.search_bar.set_visible(True)
        self.app_window.header_bar.set_visible(True)
        self.visible_children(True, None)
        self.details.set_visible(True)
        results_context = self.get_style_context()
        results_context.remove_class("fullscreen")
        results_context.add_class("results")

        set_width = int(self.app_orig_width - self.window_to_player_box_padding)
        set_height = int(set_width / 1.77)

        self.resize_player(set_width, set_height)
        self.app_window.resize(self.app_orig_width, self.app_orig_height)
        self.app_window.results_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    @Gtk.Template.Callback()
    def seek_slider(self, scale):
        seek = scale.get_value()

        # allow seeking when playing
        self.player.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek * Gst.SECOND / self.percent)

    def poll_mouse(self):
        if self.controls_box.get_visible():
            self.controls_box.set_visible(False)

    @Gtk.Template.Callback()
    def mouse_move(self, event, data):
        if not self.controls_box.get_visible():
            self.controls_box.set_visible(True)
        GLib.timeout_add_seconds(3, self.poll_mouse)

    @Gtk.Template.Callback()
    def swallow_slider_scroll_event(self, event, data):
        return True
