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
from gi.repository import Gdk, Gtk, Handy

Handy.init()

from .menu import Menu
from .history import HistoryBox
from .results import ResultsBox
from .instances import Instances

# plugin style
from .search import Search

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

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
    history_list = Gtk.Template.Child()
    history_toggle_button = Gtk.Template.Child()

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
        self.inhibit_cookie = 0
        self.strong_instances = []
        self.results_meta = []
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

#        # this will check if history exists, then show it instead of Status Page
#        self.show_history_if_exists()

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

        self.search_back_stack.set_visible_child_name("search_toggle_button")
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
        # this is called both from script an toggle button
        # to avoid recursive calling, the script will
        # set the toggle active and then return here from
        # the active toggle to show the stack
        if self.history_toggle_button.get_active():
            self.main_stack.set_visible_child_name("history_box")

#            # grab history from user history
#            self.add_history_row("1", "test", "2021-06-19 15:34")
#            self.add_history_row("2", "this is a really long test I did yesterday or the day before", "2021-06-19 15:33")

        else:
            self.history_toggle_button.set_active(True)


    def add_history_row(self, history_id, label, datetime):
        history_box = HistoryBox(self)
        self.history_list.add(history_box)
        history_box.history_id.set_label(history_id)
        history_box.search_term.set_label(label)
        history_box.search_term.set_tooltip_text(label)
        history_box.date_time.set_label(datetime)

    @Gtk.Template.Callback()
    def history_clear_all(self, button):
        children = self.history_list.get_children()
        for child in children:
            # delete it from the history file too
            child.destroy()

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
            focus_child.get_child().pause_button(None)
        else:
            focus_child.get_child().play_button(None)

#    @Gtk.Template.Callback()
#    def open_primary_menu(self, widget, ev):
#        print("in open primary menu")

    def get_scroller_list(self):
        if self.lists_stack.get_visible_child_name() == "playlist_scroller":
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

    def get_all_flowboxes(self):
        flowboxes = self.results_list.get_children()
        flowboxes.extend(self.playlist_list.get_children())
        return flowboxes

    def pause_all(self, active_window):
        flowboxes = self.get_all_flowboxes()
        for flowbox in flowboxes:
            if flowbox:
                result_window = flowbox.get_child()
                if result_window != active_window:
                    flowbox.get_child().null_out_player()

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

    def volume_up_keypress(self):
        current_volume = self.menu.volume.get_value()
        louder = 100
        if current_volume <= 90:
            louder = current_volume + 10
        self.menu.volume.set_value(louder)
        self.focus_child()

    def volume_down_keypress(self):
        current_volume = self.menu.volume.get_value()
        quieter = 0
        if current_volume >= 10:
            quieter = current_volume - 10
        self.menu.volume.set_value(quieter)
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
