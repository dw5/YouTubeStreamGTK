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

from .search import Search

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
        self.error_box.set_visible(False)
        self.error_heading.set_label("...")
        self.error_text.set_label("...")
        self.results_window.set_visible(False)
        self.spinner.set_visible(True)

        # insert spinner
        search_query = search_box.get_text()
        search = Search(app_window = self, query = search_query)

#    @Gtk.Template.Callback()
#    def keypress_listener(self, widget, ev):
#        key = Gdk.keyval_name(ev.keyval)
#        if key == "k":
#            # do stuff

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/stream.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
