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
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gtk, Handy

Handy.init()

from .results import ResultsBox
from .search import Search

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

    search_bar_toggle = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()

    status_page = Gtk.Template.Child()
    results_window = Gtk.Template.Child()
    results_list = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def search_toggle(self, widget):
        # toggle the True/False from what is current
        self.search_bar.set_visible(self.search_bar_toggle.get_active())

    def clear_entries(self):
        children = self.results_list.get_children()
        for child in children:
            child.destroy()

    @Gtk.Template.Callback()
    def search_entry(self, widget):
        self.status_page.set_visible(False)
        self.results_window.set_visible(True)

        self.clear_entries()

        # get search results
        search_results = Search(query = widget.get_text())

        # iterate per video row
        for video_meta in search_results.json:
            results_box = ResultsBox()
            self.results_list.add(results_box)

            results_box.setup_stream(video_meta)

            # one entry for now
            break

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
