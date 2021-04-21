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
from .results import ResultsBox
from .instances import Instances

# plugin style
from .search import Search as DefaultSearch

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

    header_bar = Gtk.Template.Child()
    volume = Gtk.Template.Child()
    status_icon = Gtk.Template.Child()

    search_bar_toggle = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()

    menu_button = Gtk.Template.Child()

    status_page = Gtk.Template.Child()
    status_spinner = Gtk.Template.Child()
    error_box = Gtk.Template.Child()
    error_heading = Gtk.Template.Child()
    error_text = Gtk.Template.Child()

    scroller = Gtk.Template.Child()
    results_list = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = kwargs.get('application', None)

        self.is_playing = False
        self.is_fullscreen = False
        self.inhibit_cookie = 0
        self.strong_instances = []
        self.video_results_meta = []
        instances = Instances(app_window = self)
        instances.get_strong_instances()

        self.menu = Menu(app_window = self)
        self.menu_button.set_popover(self.menu)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/stream.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @Gtk.Template.Callback()
    def search_toggle(self, toggle_button):
        # toggle the True/False from what is current
        self.search_bar.set_visible(self.search_bar_toggle.get_active())

    @Gtk.Template.Callback()
    def clear_results(self, start_pos, end_pos, data):
        # only clear results on cleared search bar (or called directly)
        if end_pos == 0:
            self.video_results_meta = []
            children = self.results_list.get_children()
            for child in children:
                child.destroy()

            self.hide_error_box()
            self.scroller.set_visible(False)
            self.status_page.set_visible(True)

    @Gtk.Template.Callback()
    def search_entry(self, search_box):
        self.clear_results(0, 0, None)
        self.status_page.set_visible(False)

        self.hide_error_box()
        self.scroller.set_visible(False)

        self.search_query = search_box.get_text()

        self.page_results = 1

        # determine app window size at time of search
        size = self.get_size()
        self.app_orig_width = size.width
        self.app_orig_height = size.height

        if not self.strong_instances:
            self.show_error_box("Service Failure",
                "No strong video server instances found yet. Try again shortly.")
        else:
            self.search = DefaultSearch(app_window = self,
                                   toggle_status_spinner = self.toggle_status_spinner,
                                   scroller = self.scroller,
                                   add_result_meta = self.add_result_meta)
            self.search.do_search(query = self.search_query, page = self.page_results)

    def toggle_status_spinner(self, toggle):
        self.status_spinner.set_visible(toggle)
        self.status_icon.set_visible(not toggle)

    def add_result_meta(self, video_meta):
        self.video_results_meta.append(video_meta)
        index_meta = len(self.video_results_meta) - 1
        self.add_result(index_meta)

    def add_result(self, index):
        results_box = ResultsBox(self)
        self.results_list.add(results_box)

        video_meta = self.video_results_meta[index]
        results_box.setup_stream(video_meta)

    @Gtk.Template.Callback()
    def load_more(self, event, data):
        vadj = self.scroller.get_vadjustment()
        position = vadj.get_value()
        upper = vadj.get_upper()
        page_size = vadj.get_page_size()

        self.page_upper = upper
        if position + page_size >= upper:
            self.page_results += 1
            self.search.do_search(query = self.search_query, page = self.page_results)

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

    def autoplay_next(self):
        if self.menu.autoplay_toggle.get_active():
            focus_child = self.results_list.get_focus_child()
            if focus_child:
                focus_index = focus_child.get_index()
                focus_next = self.results_list.get_child_at_index(focus_index + 1)
                if focus_next:
                    self.play_pause_toggle(focus_next)

    @Gtk.Template.Callback()
    def keypress_listener(self, widget, ev):
        focus_child = self.results_list.get_focus_child()
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

    def pause_all(self, active_window):
        flowboxes = self.results_list.get_children()
        for flowbox in flowboxes:
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

    def hide_error_box(self):
        self.error_box.set_visible(False)
        self.error_heading.set_label("Error")
        self.error_text.set_label("...")

    def show_error_box(self, heading, text):
        self.toggle_status_spinner(False)
        self.error_box.set_visible(True)
        self.error_heading.set_label(heading)
        self.error_text.set_label(text)

    @Gtk.Template.Callback()
    def swallow_fullscreen_scroll_event(self, event, data):
        if self.is_fullscreen:
            return True

    @Gtk.Template.Callback()
    def volume_change(self, event, data):
        self.volume_slider(event.get_value())

    def volume_slider(self, volume_value):
        children = self.results_list.get_children()
        for child in children:
            child.get_child().player.set_property("volume", volume_value)

    def focus_child(self):
        # grab focus of playing video on keypress
        focus_child = self.results_list.get_focus_child()
        if focus_child:
            focus_child.get_child().box_grab_focus()

    def volume_up_keypress(self):
        current_volume = self.volume.get_value()
        louder = 1.0
        if current_volume <= 0.9:
            louder = current_volume + 0.1
        self.volume.set_value(louder)
        self.focus_child()

    def volume_down_keypress(self):
        current_volume = self.volume.get_value()
        quieter = 0
        if current_volume >= 0.1:
            quieter = current_volume - 0.1
        self.volume.set_value(quieter)
        self.focus_child()
