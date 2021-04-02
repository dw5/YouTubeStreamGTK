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

import logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

gi.require_version('Handy', '1')
from gi.repository import Handy
Handy.init()

from .results import ResultsBox

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

    search_button = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()

    status_page = Gtk.Template.Child()
    results_window = Gtk.Template.Child()
    results_list = Gtk.Template.Child()

    def search_button_cb(self, widget):
        # toggle the True/False from what is current
        self.search_bar.set_visible(self.search_button.get_active())

    def search_entry_cb(self, widget, entry):
        entry_text = entry.get_text()
        print("Text entry: " + entry_text)
        self.status_page.set_visible(False)
        self.results_window.set_visible(True)

        results_box = ResultsBox()

        self.results_list.add(results_box)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.search_button.connect("clicked", self.search_button_cb)
        self.search_entry.connect("changed", self.search_entry_cb, self.search_entry)


    def play_button(self, button):
        logging.error('play_button')
        print("play_button it!")

    def pause_button(self, button):
        logging.error('pause_button')
        print("pause_button it!")
