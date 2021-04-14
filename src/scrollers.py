# scrollers.py
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
from gi.repository import Gtk

from .results import ResultsBox

@Gtk.Template(resource_path='/sm/puri/Stream/ui/scrollers.ui')
class ScrollerBox(Gtk.ScrolledWindow):
    __gtype_name__ = 'ScrollerBox'

    results_list = Gtk.Template.Child()
    scroller_error_box = Gtk.Template.Child()
    scroller_error_heading = Gtk.Template.Child()
    scroller_error_text = Gtk.Template.Child()

    def __init__(self, app_window, priority_index, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window
        self.priority_index = priority_index

    def add_result(self, video_meta):
        results_box = ResultsBox(self.app_window, self.priority_index)
        self.results_list.add(results_box)

        results_box.setup_stream(video_meta)

    def hide_scroller_error_box(self):
        self.results_list.set_visible(True)
        self.scroller_error_box.set_visible(False)
        self.scroller_error_heading.set_label("Error")
        self.scroller_error_text.set_label("...")

    def show_scroller_error_box(self, heading, text):
        self.results_list.set_visible(False)
        self.scroller_error_box.set_visible(True)
        self.scroller_error_heading.set_label(heading)
        self.scroller_error_text.set_label(text)

    @Gtk.Template.Callback()
    def swallow_fullscreen_scroll_event(self, event, data):
        if self.app_window.is_fullscreen:
            return True
