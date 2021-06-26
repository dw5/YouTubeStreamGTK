# results.py
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
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gst, Gtk

Gst.init(None)
Gst.init_check(None)

from .search import Search

@Gtk.Template(resource_path='/sm/puri/Stream/ui/results.ui')
class ResultsBox(Gtk.Box):
    __gtype_name__ = 'ResultsBox'

    player_box = Gtk.Template.Child()
    poster_image = Gtk.Template.Child()
    controls_box = Gtk.Template.Child()
    event_box = Gtk.Template.Child()
    play_pause_stack = Gtk.Template.Child()

    slider = Gtk.Template.Child()
    time_viewed = Gtk.Template.Child()
    time_remaining = Gtk.Template.Child()
    playlist_overlay = Gtk.Template.Child()
    playlist_label = Gtk.Template.Child()

    audio_dl = Gtk.Template.Child()
    audio_dl_image = Gtk.Template.Child()
    video_dl = Gtk.Template.Child()
    video_dl_image = Gtk.Template.Child()

    fullscreen = Gtk.Template.Child()
    unfullscreen = Gtk.Template.Child()

    details = Gtk.Template.Child()
    title = Gtk.Template.Child()
    channel = Gtk.Template.Child()
    duration = Gtk.Template.Child()

    window_to_results_margin = 8
    window_to_player_box_margin = 28

    def __init__(self, app_window, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window

        # listen for motion on the player box for controls show/hide
        self.event_box.add_events(Gdk.EventMask.POINTER_MOTION_MASK)

        # init gstreamer player
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.sink = Gst.ElementFactory.make("gtksink")

        self.video_widget = self.sink.get_property("widget")

        self.player_box.add(self.video_widget)

        self.set_player_box_size()

    def set_player_box_size(self):
        # setup player box sizing based on app window (re)size
        size = self.app_window.get_size()

        self.app_last_width = size.width
        self.app_last_height = size.height

        # do ratio calculation from width (16:9 or 1.77)
        self.video_box_width = self.app_window.video_size_active
        self.video_box_height = int(self.video_box_width / 1.77)

        self.player_box.set_size_request(self.video_box_width, self.video_box_height)
        self.poster_image.set_size_request(self.video_box_width, self.video_box_height)
        self.video_widget.set_size_request(self.video_box_width, self.video_box_height)

        # this is a HdyClamp to tighten the box around the dynamic
        # player box size (determined by window size at time of search)
        # not allowing long text titles to expand the results window
        results_width = int(self.app_window.video_size_active + self.window_to_player_box_margin)
        self.app_window.results_clamp.set_property('maximum-size', results_width)
        self.app_window.results_clamp.set_property('tightening-threshold', results_width)
        self.app_window.playlist_clamp.set_property('maximum-size', results_width)
        self.app_window.playlist_clamp.set_property('tightening-threshold', results_width)

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
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(async_res)
        self.poster_image.set_from_pixbuf(self.pixbuf)

    def stream_at_scale_async(self, poster_file):
        stream = poster_file.read_async(0, None,
                self.on_file_read, None)

    def setup_stream(self, meta):
        if 'type' in meta:
            self.type = meta['type']
            if meta['type'] == 'video':
                self.setup_meta(meta)
                self.setup_video(meta)
            elif meta['type'] == 'playlist':
                self.setup_meta(meta)
                self.setup_playlist(meta)

    def setup_meta(self, meta):
        self.meta_title = meta['title']
        meta_channel = meta['author']
        poster_uri = meta['poster_uri']
        # initialize video duration
        self.video_duration = 0

        self.title.set_label(self.meta_title)
        self.title.set_tooltip_text(self.meta_title)
        self.channel.set_label(meta_channel)
        self.channel.set_tooltip_text(meta_channel)

        poster_file = Gio.File.new_for_uri(poster_uri)
        self.stream_at_scale_async(poster_file)

    def setup_playlist(self, playlist_meta):
        self.app_window.playlist_id = playlist_meta['playlistId']
        self.playlist_overlay.set_visible(True)
        self.controls_box.set_visible(False)

        # switch to playlist display
        self.duration.set_visible(False)
        self.playlist_label.set_visible(True)

    def setup_video(self, video_meta):
        self.time_viewed.set_label('0:00')
        self.video_duration = self.get_readable_seconds(video_meta['lengthSeconds'])
        self.duration.set_label(self.video_duration)
        self.time_remaining.set_label(f"-{self.video_duration}")

        self.player.set_property("uri", video_meta['video_uri'])
        self.player.set_property("video-sink", self.sink)

        if 'audio_dl_uri' in video_meta:
            if video_meta['audio_dl_uri']:
                # enable download button
                self.audio_dl.set_sensitive(True)
                # set the download uri for download button
                self.audio_dl_uri = video_meta['audio_dl_uri']

        if 'video_dl_uri' in video_meta:
            if video_meta['video_dl_uri']:
                # enable download button
                self.video_dl.set_sensitive(True)
                # set the download uri for download button
                self.video_dl_uri = video_meta['video_dl_uri']

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

            if duration > 0 and position > 0:
                viewed_seconds = int(position / Gst.SECOND)
                remaining_seconds = int((duration - position) / Gst.SECOND)
                viewed = self.get_readable_seconds(viewed_seconds)
                remaining = self.get_readable_seconds(remaining_seconds)

                self.time_viewed.set_label(viewed)
                self.time_remaining.set_label(f"-{remaining}")

                if int(position / Gst.SECOND) >= int(duration / Gst.SECOND):
                    GLib.timeout_add(500, self.null_out_player)
                    GLib.timeout_add(1200, self.app_window.next_playback_action)

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

        dest_title = self.strictify_name(self.meta_title)
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

        dest_title = self.strictify_name(self.meta_title)
        dest_path = f"{dest_dir}/{dest_title}.{dest_ext}"
        dest = Gio.File.new_for_path(dest_path)
        flags = Gio.FileCopyFlags
        dl_stream.copy_async(dest,
                # bitwise or (not tuple) for multiple flags
                Gio.FileCopyFlags.OVERWRITE |
                Gio.FileCopyFlags.ALL_METADATA |
                Gio.FileCopyFlags.TARGET_DEFAULT_PERMS,
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

    def box_grab_focus(self):
        list = self.app_window.get_scroller_list()
        if list.get_focus_child():
            # grab the parent flowboxchild and focus it
            # to snap it into frame
            list.get_focus_child().grab_focus()
        # grab the result box to enable future focus snapping
        self.grab_focus()

    @Gtk.Template.Callback()
    def play_button(self, button):
        self.box_grab_focus()
        # loop through all child results pausing them
        self.app_window.pause_all(self)

        self.play_pause_stack.set_visible_child_name("pause")
        self.app_window.is_playing = True
        self.app_window.inhibit_app()
        self.player.set_state(Gst.State.PLAYING)

        # hide the poster, show the video
        self.player_box.show_all()
        self.poster_image.hide()

        # initialize the slider
        self.update_slider()
        # allow seeking
        self.slider.set_sensitive(True)

        app_volume = self.app_window.menu.volume.get_value() / 100
        self.player.set_property("volume", app_volume)

        # grab the speed from menu
        speed = self.app_window.menu.speed.get_value()
        # something like this sudo code:
        # self.player.set_property("speed", speed)

        # update slider to track video time in slider
        GLib.timeout_add_seconds(1, self.update_slider)

    def null_out_player(self):
        self.inactivate_player()
        self.player.set_state(Gst.State.NULL)
        self.slider.set_value(0)
        self.time_viewed.set_label('0:00')
        self.time_remaining.set_label(f"-{self.video_duration}")
        self.video_widget.hide()
        self.poster_image.show()

    @Gtk.Template.Callback()
    def pause_button(self, button):
        self.box_grab_focus()
        self.inactivate_player()
        self.player.set_state(Gst.State.PAUSED)

    def inactivate_player(self):
        self.play_pause_stack.set_visible_child_name("play")
        self.app_window.is_playing = False
        self.app_window.uninhibit_app()

    def resize_results(self):
        self.poster_image.clear()

        # resize the player boxes to the new window size
        self.set_player_box_size()

        # check if there is an original pixbuf to resize
        if hasattr(self, "pixbuf"):
            resize_pixbuf = GdkPixbuf.Pixbuf.scale_simple(self.pixbuf,
                                self.video_box_width, self.video_box_height,
                                GdkPixbuf.InterpType.BILINEAR)

            self.poster_image.set_from_pixbuf(resize_pixbuf)

    def resize_player(self, width, height):
        self.poster_image.set_size_request(width, height)
        self.video_widget.set_size_request(width, height)

    @Gtk.Template.Callback()
    def fullscreen_button(self, button):
        self.fullscreen.set_visible(False)
        self.unfullscreen.set_visible(True)
        self.app_window.fullscreen()
        self.app_window.is_fullscreen = True
        self.app_window.header_bar.set_visible(False)
        self.details.set_visible(False)

        self.app_window.search_bar.set_visible(False)

        set_width = int(Gdk.Screen.get_default().get_width())
        set_height = int(Gdk.Screen.get_default().get_height())
        self.resize_player(set_width, set_height)

        results_context = self.get_style_context()
        results_context.remove_class("results")
        results_context.add_class("fullscreen")

        GLib.timeout_add(50, self.box_grab_focus)

        # horizonal scrollbar, vertical scrollbar (do last)
        scroller = self.app_window.scroller
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        scroller.set_kinetic_scrolling(False)

    @Gtk.Template.Callback()
    def unfullscreen_button(self, button):
        self.fullscreen.set_visible(True)
        self.unfullscreen.set_visible(False)
        self.app_window.unfullscreen()
        self.app_window.is_fullscreen = False
        # if on scroller show search toggle active result
        self.app_window.header_bar.set_visible(True)
        self.details.set_visible(True)

        if self.app_window.lists_stack.get_visible_child_name() == "scroller":
            self.app_window.search_bar.set_visible(self.app_window.search_bar_toggle.get_active())

        results_context = self.get_style_context()
        results_context.remove_class("fullscreen")
        results_context.add_class("results")

        self.resize_player(self.video_box_width, self.video_box_height)
        self.app_window.resize(self.app_last_width, self.app_last_height)

        scroller = self.app_window.scroller
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_kinetic_scrolling(True)

        GLib.timeout_add(50, self.box_grab_focus)

    @Gtk.Template.Callback()
    def seek_slider(self, scale):
        seek = scale.get_value()

        # allow seeking when playing
        self.player.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek * Gst.SECOND / self.percent)

    def reverse_keypress(self):
        self.box_grab_focus()
        if self.app_window.is_playing:
            success, position = self.player.query_position(Gst.Format.TIME)
            seek = 0
            # extra fast keypresses yield a -1 for position
            if position > 0:
                if position / Gst.SECOND >= 10:
                    seek = position - (10 * Gst.SECOND)
                self.player.seek_simple(Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seek)

    def forward_keypress(self):
        self.box_grab_focus()
        if self.app_window.is_playing:
            p_success, position = self.player.query_position(Gst.Format.TIME)
            d_success, duration = self.player.query_duration(Gst.Format.TIME)
            seek = duration
            # extra fast keypresses yield a -1 for position
            if position > 0:
                if position <= duration - (10 * Gst.SECOND):
                    seek = position + (10 * Gst.SECOND)
                self.player.seek_simple(Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seek)

    def poll_mouse(self):
        now_is = int(GLib.get_current_time())
        if (int(now_is) - (self.last_move)) >= 2:
            if self.controls_box.get_visible():
                self.controls_box.set_visible(False)

    @Gtk.Template.Callback()
    def event_mouse_click(self, event, data):
        if self.playlist_overlay.get_visible():
            self.app_window.pause_all(self)
            self.app_window.clear_playlist(0, 0, None)

            self.app_window.search_bar_toggle.set_visible(False)
            self.app_window.search_bar.set_visible(False)
            self.app_window.header_bar.set_property('title', "Playlist")

            self.app_window.search_back_stack.set_visible_child_name("back_button")

            self.app_window.lists_stack.set_visible_child_name("playlist_scroller")

            self.app_window.playlist_search = Search(app_window = self.app_window,
                toggle_status_spinner = self.app_window.toggle_status_spinner,
                add_result_meta = self.app_window.add_playlist_result_meta)
            self.app_window.playlist_search.do_playlist(playlist_id = self.app_window.playlist_id, page = self.app_window.page_playlist)

        else:
            if self.app_window.is_playing:
                self.pause_button(None)
            else:
                self.play_button(None)
            self.event_mouse_action(event, data)

    @Gtk.Template.Callback()
    def event_mouse_action(self, event, data):
        if not self.playlist_overlay.get_visible():
            self.last_move = int(GLib.get_current_time())
            GLib.timeout_add_seconds(2, self.poll_mouse)
            if not self.controls_box.get_visible():
                self.controls_box.set_visible(True)

    @Gtk.Template.Callback()
    def swallow_slider_scroll_event(self, event, data):
        return True
