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
from gi.repository import GLib, Gtk, Gdk

gi.require_version('Handy', '1')
from gi.repository import Handy
Handy.init()

@Gtk.Template(resource_path='/sm/puri/Stream/ui/results.ui')
class ResultsBox(Gtk.Box):
    __gtype_name__ = 'ResultsBox'

    play = Gtk.Template.Child()
    pause = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/results.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @Gtk.Template.Callback()
    def audio_dl_button(self, button):
        print("audio_dl_button")

    @Gtk.Template.Callback()
    def video_dl_button(self, button):
        print("video_dl_button")

    @Gtk.Template.Callback()
    def play_button(self, button):
        self.play.set_visible(False)
        self.pause.set_visible(True)
        print("play_button")

    @Gtk.Template.Callback()
    def pause_button(self, button):
        self.play.set_visible(True)
        self.pause.set_visible(False)
        print("pause_button")

    @Gtk.Template.Callback()
    def speed_button(self, button):
        print("speed_button")

    @Gtk.Template.Callback()
    def fullscreen_button(self, button):
        print("fullscreen_button")
