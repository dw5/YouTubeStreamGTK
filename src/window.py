# window.py
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
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gdk, GLib, Gtk, Handy

Handy.init()

from .menu import Menu
from .history import HistoryBox
from .results import ResultsBox
from .instances import Instances

import json

# plugin style
from .search import Search

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

    osd_overlay = Gtk.Template.Child()
    osd_icon = Gtk.Template.Child()
    osd_label = Gtk.Template.Child()

    user_data_dir = GLib.get_user_data_dir()
    header_bar = Gtk.Template.Child()
    status_icon = Gtk.Template.Child()

    search_bar_toggle = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry_box = Gtk.Template.Child()

    search_back_stack = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()

    main_stack = Gtk.Template.Child()
    status_stack = Gtk.Template.Child()
    status_page = Gtk.Template.Child()
    status_spinner = Gtk.Template.Child()

    error_heading = Gtk.Template.Child()
    error_text = Gtk.Template.Child()
    error_action_button = Gtk.Template.Child()

    history_box = Gtk.Template.Child()
    history_toggle_button = Gtk.Template.Child()

    history_file = f"{user_data_dir}/history.json"
    history_json = { 'search_history': [],
                     'videos_history': [] }

    search_history_list = Gtk.Template.Child()
    videos_history_list = Gtk.Template.Child()

    # lists stack holds both the scroller ScrollWindow
    # and the playlist_scroller ScrollWindow
    lists_stack = Gtk.Template.Child()

    scroller = Gtk.Template.Child()
    results_list = Gtk.Template.Child()
    results_clamp = Gtk.Template.Child()

    playlist_list = Gtk.Template.Child()
    playlist_clamp = Gtk.Template.Child()

    # magic sizes:
    # 16:9 (1.77)
    # initial window width 1920 / 2 = 960
    # initial video size 854x480
    # small video size 332x186
    # resize threshold 854 + margin (28) = 882
    window_resize_threshold = 882
    video_large_width = 854
    video_small_width = 332
    video_size_active = video_small_width
    window_last_size = 'big'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = kwargs.get('application', None)

        self.is_playing = False
        self.is_fullscreen = False
        self.history_rendered = False
        self.inhibit_cookie = 0
        self.strong_instances = []
        self.results_meta = []
        self.videos_history_results_meta = []
        self.playlist_results_meta = []
        self.instances = Instances(app_window = self)
        self.instances.get_strong_instances()

        self.menu = Menu(app_window = self)
        self.menu_button.set_popover(self.menu)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/stream.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def strong_instance_found(self):
        if self.history_rendered:
            return False

        # Check if history exists, then show it instead of Status Page
        self.show_history_if_exists()

    @Gtk.Template.Callback()
    def search_toggle(self, toggle_button):
        # toggle the True/False from what is current
        self.search_bar.set_visible(self.search_bar_toggle.get_active())

    @Gtk.Template.Callback()
    def back_navigate(self, button):
        self.pause_all(None)
        # restore search visible
        self.search_bar_toggle.set_visible(True)
        self.search_bar_toggle.set_active(True)
        self.search_bar.set_visible(True)
        self.header_bar.set_property('title', "Stream")

        self.search_back_stack.set_visible_child_name("search_bar_toggle")
        self.lists_stack.set_visible_child_name("scroller")

    # this is called from code and from the ui XML upon
    # delete-text button press in search-entry
    @Gtk.Template.Callback()
    def clear_results(self, start_pos, end_pos, data):
        # only clear results on cleared search bar (or called directly)
        if end_pos == 0:
            self.page_results = 1
            self.results_meta = []
            children = self.results_list.get_children()
            for child in children:
                child.destroy()

            self.clear_error_box()
            self.main_stack.set_visible_child_name("status_page")
            self.clear_playlist(0, 0, None)

    def clear_playlist(self, start_pos, end_pos, data):
        self.page_playlist = 1
        self.playlist_results_meta = []
        children = self.playlist_list.get_children()
        for child in children:
            child.destroy()

    @Gtk.Template.Callback()
    def search_entry(self, search_box):
        self.clear_results(0, 0, None)
        self.clear_error_box()
        self.history_toggle_button.set_active(False)
        self.main_stack.set_visible_child_name("lists_stack")

        self.search_query = search_box.get_text()

        # write search to history
        self.write_search_history(self.search_query)

        if not self.strong_instances:
            self.show_error_box("Service Failure",
                                "No strong instances found to do search against.")
            self.instances.get_strong_instances()
        else:
            self.search = Search(app_window = self,
                toggle_status_spinner = self.toggle_status_spinner,
                add_result_meta = self.add_result_meta)
            self.search.do_search(query = self.search_query, page = self.page_results)

    def toggle_status_spinner(self, toggle):
        if toggle:
            self.status_stack.set_visible_child_name("status_spinner")
        else:
            self.status_stack.set_visible_child_name("status_icon")

    @Gtk.Template.Callback()
    def history_toggle(self, toggle_button):
        if toggle_button.get_active():
            self.show_history_if_exists()
        else:
            self.main_stack.set_visible_child_name("lists_stack")

    def show_history_if_exists(self):
        if not self.strong_instances:
            return False

        # this is called both from script an toggle button
        # to avoid recursive calling, the script will
        # set the toggle active and then return here from
        # the active toggle to show the stack
        if self.history_toggle_button.get_active():
            self.main_stack.set_visible_child_name("history_box")

            # grab history from user history
            try:
                with open(self.history_file) as file:
                   self.history_json = json.load(file)
            except:
                self.main_stack.set_visible_child_name("status_page")

            for history_box in self.search_history_list:
                history_box.destroy()

            for history_box in self.videos_history_list:
                history_box.destroy()

            # show reverse sorted history of last 10 searches
            for history in list(reversed(self.history_json['search_history'][-10::])):
                self.add_search_history_row(history)

            # show reverse sorted history of last 10 videos
            for history in list(reversed(self.history_json['videos_history'][-10::])):
                self.add_videos_history_row(history)

            self.history_rendered = True
        else:
            self.history_toggle_button.set_active(True)

    def add_search_history_row(self, history_value):
        history_box = HistoryBox(self)
        self.search_history_list.add(history_box)
        history_box.search_term.set_label(history_value)
        history_box.search_term.set_tooltip_text(history_value)

    def add_videos_history_row(self, history_value):
        # grab the meta from search
        single_video_search = Search(app_window = self,
            toggle_status_spinner = self.toggle_status_spinner,
            add_result_meta = self.add_videos_history_result_meta)
        single_video_search.do_single_video_search(video_id = history_value)

    @Gtk.Template.Callback()
    def search_history_clear_all(self, button):
        children = self.search_history_list.get_children()
        for child in children:
            if child:
                history_child = child.get_child()
                if history_child:
                    history_child.search_history_row_delete(None)

    @Gtk.Template.Callback()
    def videos_history_clear_all(self, button):
        children = self.videos_history_list.get_children()
        for child in children:
            if child:
                history_child = child.get_child()
                if history_child:
                    history_child.videos_history_row_delete(None)

    def get_history_json(self):
        try:
            with open(self.history_file) as file:
                self.history_json = json.load(file)
                return True
        except:
            return False

    def write_history_json(self):
        try:
            with open(self.history_file, 'w') as file:
                json.dump(self.history_json, file)
                return(True)
        except:
            return False

    def search_history_json_remove(self, history_value):
        if self.get_history_json():
            # remove old (matching query) if exists
            if history_value in self.history_json['search_history']:
                self.history_json['search_history'].remove(history_value)

        self.write_history_json()

    def videos_history_json_remove(self, history_value):
        if self.get_history_json():
            # remove old (matching query) if exists
            if history_value in self.history_json['videos_history']:
                self.history_json['videos_history'].remove(history_value)

        self.write_history_json()

    def write_search_history(self, history_value):
        if not self.menu.incognito_mode.get_active():
            self.search_history_json_remove(history_value)
            # append new history_value
            self.history_json['search_history'].append(history_value)
            self.write_history_json()

    def write_videos_history(self, history_value):
        if not self.menu.incognito_mode.get_active():
            self.videos_history_json_remove(history_value)
            # append new history_value
            self.history_json['videos_history'].append(history_value)
            self.write_history_json()

    def add_result_meta(self, meta):
        # stores an array of results for playlists and videos
        self.results_meta.append(meta)
        index_meta = len(self.results_meta) - 1
        self.add_result(index_meta)

    def add_result(self, index):
        results_box = ResultsBox(self)
        self.results_list.add(results_box)

        meta = self.results_meta[index]
        results_box.setup_stream(meta)

    def add_videos_history_result_meta(self, meta):
        self.videos_history_results_meta.append(meta)
        index_meta = len(self.videos_history_results_meta) - 1
        self.add_videos_history_result(index_meta)

    def add_videos_history_result(self, index):
        videos_history_result_box = ResultsBox(self)
        self.videos_history_list.add(videos_history_result_box)

        meta = self.videos_history_results_meta[index]
        videos_history_result_box.setup_stream(meta)

    def add_playlist_result_meta(self, meta):
        # stores an array of results for playlists and videos
        self.playlist_results_meta.append(meta)
        index_playlist_meta = len(self.playlist_results_meta) - 1
        self.add_playlist_result(index_playlist_meta)

    def add_playlist_result(self, index):
        playlist_results_box = ResultsBox(self)
        self.playlist_list.add(playlist_results_box)

        meta = self.playlist_results_meta[index]
        playlist_results_box.setup_stream(meta)

    @Gtk.Template.Callback()
    def load_more(self, event, data):
        vadj = self.scroller.get_vadjustment()
        position = vadj.get_value()
        upper = vadj.get_upper()
        page_size = vadj.get_page_size()

        if position + page_size >= upper:
            self.page_results += 1
            self.search.do_search(query = self.search_query, page = self.page_results)

#    @Gtk.Template.Callback()
#    def load_more_playlist(self, event, data):
#        vadj = self.playlist_scroller.get_vadjustment()
#        position = vadj.get_value()
#        upper = vadj.get_upper()
#        page_size = vadj.get_page_size()
#
#        if position + page_size >= upper:
#            self.page_playlist += 1
#            # initially created in results.py upon playlist creation
#            self.playlist_search.do_playlist(playlist_id = self.playlist_id, page = self.page_playlist)
#
    def fullscreen_toggle(self, focus_child):
        if self.is_fullscreen:
            focus_child.get_child().unfullscreen_button(None)
        else:
            focus_child.get_child().fullscreen_button(None)

    def play_pause_toggle(self, focus_child):
        if self.is_playing:
            self.osd_display_show("media-playback-pause-symbolic", "Pause")
            focus_child.get_child().pause_button(None)
        else:
            self.osd_display_show("media-playback-start-symbolic", "Play")
            focus_child.get_child().play_button(None)

#    @Gtk.Template.Callback()
#    def open_primary_menu(self, widget, ev):
#        print("in open primary menu")

    def get_scroller_list(self):
        if self.history_toggle_button.get_active():
            return self.videos_history_list
        elif self.lists_stack.get_visible_child_name() == "playlist_scroller":
            return self.playlist_list
        else:
            return self.results_list

    def next_playback_action(self):
        list = self.get_scroller_list()
        focus_child = list.get_focus_child()
        if focus_child:
            action = "one"
            stack = self.menu.mode_switcher.get_stack()
            if stack:
                action = stack.get_visible_child_name()

            # check if video loop override is on
            if action == "loop":
                self.play_pause_toggle(focus_child)

            # otherwise, check if user wants to auto play through list
            elif action == "auto":
                focus_index = focus_child.get_index()
                focus_next = list.get_child_at_index(focus_index + 1)
                if focus_next:
                    self.play_pause_toggle(focus_next)

    @Gtk.Template.Callback()
    def keypress_listener(self, widget, ev):
        list = self.get_scroller_list()
        focus_child = list.get_focus_child()
        if focus_child:
            # key values are from gdk/gdkkeysyms.h
            key = Gdk.keyval_name(ev.keyval)
            if key == "Escape":
                focus_child.get_child().unfullscreen_button(None)
            elif key == "space":
                self.play_pause_toggle(focus_child)
            elif key == "f":
                self.fullscreen_toggle(focus_child)
            elif key == "m":
                self.mute_keypress()
            elif key == "Up":
                self.volume_up_keypress()
                return True
            elif key == "Down":
                self.volume_down_keypress()
                return True
            elif key == "Left":
                focus_child.get_child().reverse_keypress()
                return True
            elif key == "Right":
                focus_child.get_child().forward_keypress()
                return True
            elif key == "bracketleft":
                self.speed_slower_keypress()
                return True
            elif key == "bracketright":
                self.speed_faster_keypress()
                return True

    def osd_display_show(self, icon, label):
        self.osd_label.set_label(label)
        self.osd_icon.set_property('icon-name', icon)
        self.osd_overlay.set_reveal_child(True)
        GLib.timeout_add_seconds(1, self.osd_display_hide)

    def osd_display_hide(self):
        self.osd_overlay.set_reveal_child(False)

    def get_all_flowboxes(self):
        flowboxes = self.results_list.get_children()
        flowboxes.extend(self.playlist_list.get_children())
        flowboxes.extend(self.videos_history_list.get_children())
        return flowboxes

    def pause_all(self, active_window):
        flowboxes = self.get_all_flowboxes()
        for flowbox in flowboxes:
            if flowbox:
                result_window = flowbox.get_child()
                if result_window and result_window != active_window:
                    result_window.null_out_player()

    def inhibit_app(self):
        self.inhibit_cookie = self.application.inhibit(self,
                Gtk.ApplicationInhibitFlags.IDLE |
                Gtk.ApplicationInhibitFlags.LOGOUT,
                "Stream-ing Video")

    def uninhibit_app(self):
        if self.inhibit_cookie:
            self.application.uninhibit(self.inhibit_cookie)

    def clear_error_box(self):
        self.main_stack.set_visible_child_name("lists_stack")
        self.error_heading.set_label("Error")
        self.error_text.set_label("...")

    def show_error_box(self, heading, text):
        self.toggle_status_spinner(False)
        self.main_stack.set_visible_child_name("error_box")
        self.error_heading.set_label(heading)
        self.error_text.set_label(text)

    @Gtk.Template.Callback()
    def reload_instances(self, event):
        self.status_icon.set_property('icon-name', 'content-loading-symbolic')
        self.clear_error_box()
        self.instances.get_strong_instances()

    @Gtk.Template.Callback()
    def swallow_fullscreen_scroll_event(self, event, data):
        if self.is_fullscreen:
            return True

    def focus_child(self):
        # grab focus of playing video on keypress
        list = self.get_scroller_list()
        focus_child = list.get_focus_child()
        if focus_child:
            focus_child.get_child().box_grab_focus()

    def mute_keypress(self):
        if self.menu.mute_button.get_active():
            self.menu.mute_button.set_active(False)
            current_volume = self.menu.volume.get_value()
            self.osd_display_show("audio-volume-medium-symbolic", str(int(current_volume)))
        else:
            self.menu.mute_button.set_active(True)
            self.osd_display_show("audio-volume-muted-symbolic", str(0))
        self.focus_child()

    def volume_up_keypress(self):
        current_volume = self.menu.volume.get_value()
        louder = 100
        if current_volume <= 95:
            louder = current_volume + 5
        self.menu.volume.set_value(louder)
        self.osd_display_show("audio-volume-medium-symbolic", str(int(louder)))
        self.focus_child()

    def volume_down_keypress(self):
        current_volume = self.menu.volume.get_value()
        quieter = 0
        if current_volume >= 5:
            quieter = current_volume - 5
        self.menu.volume.set_value(quieter)
        self.osd_display_show("audio-volume-low-symbolic", str(int(quieter)))
        self.focus_child()

    def speed_faster_keypress(self):
        current_speed = self.menu.speed.get_value()
        faster = current_speed + .25
        self.menu.speed.set_value(faster)
        self.focus_child()

    def speed_slower_keypress(self):
        current_speed = self.menu.speed.get_value()
        slower = current_speed - .25
        self.menu.speed.set_value(slower)
        self.focus_child()

    @Gtk.Template.Callback()
    def screen_changed(self, event, data):
        size = self.get_size()

        # get the current clamp threshold
        current_threshold = self.results_clamp.get_property('tightening-threshold')

        trigger_resize = False
        if size.width <= current_threshold and size.width <= self.window_resize_threshold:
            self.video_size_active = self.video_small_width
            if self.window_last_size == 'big':
                self.window_last_size = 'small'
                trigger_resize = True
        elif size.width > current_threshold and size.width > self.window_resize_threshold:
            self.video_size_active = self.video_large_width
            if self.window_last_size == 'small':
                self.window_last_size = 'big'
                trigger_resize = True

        if trigger_resize:
            flowboxes = self.get_all_flowboxes()
            for flowbox in flowboxes:
                if flowbox:
                    result_window = flowbox.get_child()
                    if result_window:
                        result_window.resize_results()
