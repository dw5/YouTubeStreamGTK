# menu.py
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

from .about import About
from .help import Help

@Gtk.Template(resource_path="/sm/puri/Stream/ui/menu.ui")
class Menu(Gtk.PopoverMenu):
    __gtype_name__ = 'Menu'

    autoplay_toggle = Gtk.Template.Child()

    def __init__(self, app_window, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window

    @Gtk.Template.Callback()
    def show_about(self, data):
        about = About()
        about.props.transient_for = self.app_window
        about.present()

    @Gtk.Template.Callback()
    def show_help(self, data):
        help = Help()
        help.props.transient_for = self.app_window
        help.present()
