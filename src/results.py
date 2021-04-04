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

    player_box = Gtk.Template.Child()
    poster_image = Gtk.Template.Child()
    play = Gtk.Template.Child()
    pause = Gtk.Template.Child()
    slider = Gtk.Template.Child()

    title = Gtk.Template.Child()
    channel = Gtk.Template.Child()
    duration = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/results.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # init gstreamer player
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.sink = Gst.ElementFactory.make("gtksink")

        video_widget = self.sink.get_property("widget")
        video_widget.set_size_request(332, 186)

        self.player_box.add(video_widget)

    def get_duration(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if seconds >= 3600:
            self.video_duration = f"{h:d}:{m:02d}:{s:02d}"
        else:
            self.video_duration = f"{m:d}:{s:02d}"

    def on_poster_load(self, source, async_res, user_data):
        self.poster_image.clear()
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(async_res)
        self.poster_image.set_from_pixbuf(pixbuf)


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
        result = GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(poster_file.read(),
                                                    332, 186, # width and height
                                                    True,    # preserve_aspect_ratio
                                                    None,     # cancellable
                                                    self.on_poster_load, # callback,
                                                    video_id)     # user_data


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
            
            # block seek slider function so it doesn't loop itself
            self.slider.handler_block_by_func(self.seek_slider)
            self.slider.set_value(position_value)
            self.slider.handler_unblock_by_func(self.seek_slider)
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
        GLib.timeout_add(1000, self.update_slider)

    @Gtk.Template.Callback()
    def pause_button(self, button):
        self.play.set_visible(True)
        self.pause.set_visible(False)
        self.player.set_state(Gst.State.PAUSED)
        self.is_playing = False

    @Gtk.Template.Callback()
    def speed_button(self, button):
        print("speed_button")

    @Gtk.Template.Callback()
    def fullscreen_button(self, button):
        print("fullscreen_button")

    @Gtk.Template.Callback()
    def seek_slider(self, scale):
        seek = scale.get_value()

        # allow seeking when playing
        self.player.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek * Gst.SECOND / self.percent)
