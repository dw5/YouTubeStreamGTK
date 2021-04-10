# window.py
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
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gdk, Gtk, Handy

Handy.init()

import json

from .search import Search
from .instances import Instances

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

    header_bar = Gtk.Template.Child()

    search_bar_toggle = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()

    status_page = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    error_box = Gtk.Template.Child()
    error_heading = Gtk.Template.Child()
    error_text = Gtk.Template.Child()
    results_window = Gtk.Template.Child()
    results_list = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def search_toggle(self, toggle_button):
        # toggle the True/False from what is current
        self.search_bar.set_visible(self.search_bar_toggle.get_active())

    @Gtk.Template.Callback()
    def search_entry(self, search_box):
        self.status_page.set_visible(False)
        self.hide_error_box()
        self.results_window.set_visible(False)
        self.spinner.set_visible(True)

        # insert spinner
        search_query = search_box.get_text()

        if self.strong_instances:
            search = Search(app_window = self)
            search.do_search(query = search_query)
        else:
            self.show_error_box("Service Failure",
                "No strong video server instances found yet. Try again shortly.")
    def fullscreen_toggle(self, focus_child):
        if self.is_fullscreen:
            focus_child.get_child().unfullscreen_button(None)
        else:
            focus_child.get_child().fullscreen_button(None)

    def play_pause_toggle(self, focus_child):
        if self.is_playing:
            self.pause_all()
        else:
            focus_child.get_child().play_button(None)

    @Gtk.Template.Callback()
    def keypress_listener(self, widget, ev):
        key = Gdk.keyval_name(ev.keyval)
        focus_child = self.results_list.get_focus_child()
        if focus_child:
            if key == "Escape":
                focus_child.get_child().unfullscreen_button(None)
            if key == "space":
                self.play_pause_toggle(focus_child)
            if key == "f":
                self.fullscreen_toggle(focus_child)

    @Gtk.Template.Callback()
    def swallow_fullscreen_scroll_event(self, event, data):
        if self.is_fullscreen:
            return True

    def pause_all(self):
        flowboxes = self.results_list.get_children()
        for flowbox in flowboxes:
            flowbox.get_child().pause_button(None)

    def hide_error_box(self):
        self.error_box.set_visible(False)
        self.error_heading.set_label("Error")
        self.error_text.set_label("...")

    def show_error_box(self, heading, text):
        self.spinner.set_visible(False)
        self.error_box.set_visible(True)
        self.error_heading.set_label(heading)
        self.error_text.set_label(text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.is_playing = False
        self.is_fullscreen = False
        self.strong_instances = []
        instances = Instances(app_window = self)
        instances.get_strong_instances()

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/stream.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
