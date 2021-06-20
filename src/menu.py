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

from .preferences import Preferences
from .help import Help
from .about import About

@Gtk.Template(resource_path="/sm/puri/Stream/ui/menu.ui")
class Menu(Gtk.PopoverMenu):
    __gtype_name__ = 'Menu'

    volume = Gtk.Template.Child()
    volume_icon = Gtk.Template.Child()
    speed = Gtk.Template.Child()

    mode_switcher = Gtk.Template.Child()

    def __init__(self, app_window, **kwargs):
        super().__init__(**kwargs)

        self.app_window = app_window

    @Gtk.Template.Callback()
    def volume_change(self, event):
        self.volume_setting(event.get_value())

    @Gtk.Template.Callback()
    def speed_change(self, event):
        self.speed_setting(event.get_value())

    @Gtk.Template.Callback()
    def mute_toggle(self, toggle_button):
        if toggle_button.get_active():
            self.volume_icon.set_property('icon-name', 'audio-volume-muted-symbolic')
            self.volume_setting(0)
        else:
            self.volume_icon.set_property('icon-name', 'audio-volume-medium-symbolic')
            self.volume_setting(self.volume.get_value())

    def volume_setting(self, volume_value):
        # gstreamer uses decimal 0.0 to 1.0 for volume
        volume_decimal = volume_value / 100
        list = self.app_window.get_scroller_list()
        children = list.get_children()
        for child in children:
            child.get_child().player.set_property("volume", volume_decimal)

    def speed_setting(self, speed_value):
        list = self.app_window.get_scroller_list()
        children = list.get_children()
#        for child in children:
#            # something like this sudo code:
#            child.get_child().player.set_property("speed", speed_value)

    @Gtk.Template.Callback()
    def show_preferences(self, data):
        preferences = Preferences(transient_for = self.app_window)
        preferences.present()

    @Gtk.Template.Callback()
    def show_help(self, data):
        help = Help(transient_for = self.app_window)
        help.present()

    @Gtk.Template.Callback()
    def show_about(self, data):
        about = About(transient_for = self.app_window)
        about.present()
