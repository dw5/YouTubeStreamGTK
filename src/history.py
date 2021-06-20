# history.py
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
from gi.repository import Gtk

@Gtk.Template(resource_path='/sm/puri/Stream/ui/history.ui')
class HistoryBox(Gtk.Box):
    __gtype_name__ = 'HistoryBox'

    search_term = Gtk.Template.Child()
    history_id = Gtk.Template.Child()
    date_time = Gtk.Template.Child()

    def __init__(self, app_window, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window

    @Gtk.Template.Callback()
    def history_search(self, event, data):
        self.app_window.search_entry_box.set_text(self.search_term.get_label())
        self.app_window.search_entry(self.app_window.search_entry_box)

    @Gtk.Template.Callback()
    def history_row_delete(self, event):
        #print(self.history_id.get_label())
        self.destroy()

