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

import json

from .menu import Menu
from .scrollers import ScrollerBox
from .instances import Instances

# plugin style
from .search import Search as DefaultSearch
from .iteroni import Search as PluginSearch

@Gtk.Template(resource_path='/sm/puri/Stream/ui/window.ui')
class StreamWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'StreamWindow'

    header_bar = Gtk.Template.Child()
    navigation_previous = Gtk.Template.Child()
    navigation_current = Gtk.Template.Child()
    navigation_next = Gtk.Template.Child()

    search_bar_toggle = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()

    menu_button = Gtk.Template.Child()

    status_page = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    error_box = Gtk.Template.Child()
    error_heading = Gtk.Template.Child()
    error_text = Gtk.Template.Child()

    scroller_stack = Gtk.Template.Child()


    @Gtk.Template.Callback()
    def search_toggle(self, toggle_button):
        # toggle the True/False from what is current
        self.search_bar.set_visible(self.search_bar_toggle.get_active())

    def clear_scroll_stacks(self):
        children = self.scroller_stack.get_children()
        for child in children:
            child.destroy()

    @Gtk.Template.Callback()
    def search_entry(self, search_box):
        self.stacks_list = []
        self.status_page.set_visible(False)

        self.hide_error_box()
        self.spinner.set_visible(True)

        search_query = search_box.get_text()

        self.clear_scroll_stacks()

        if not self.strong_instances:
            self.show_error_box("Service Failure",
                "No strong video server instances found yet. Try again shortly.")
        else:
            instance_index = 0
            for sort_by in ["relevance", "view_count"]:
                key = sort_by + str(instance_index)
                self.stacks_list.append(key)
                self.scroller = ScrollerBox(self, instance_index)
                self.scroller_stack.add_named(self.scroller, key)

                search = DefaultSearch(app_window = self,
                                       instance_index = instance_index,
                                       sort_by = sort_by,
                                       set_headerbar_color = self.set_headerbar_color,
                                       spinner = self.spinner,
                                       add_result = self.scroller.add_result,
                                       scroller_stack = self.scroller_stack)
                search.do_search(query = search_query)
                instance_index += 1

            key = 'plugin' + str(instance_index)
            self.stacks_list.append(key)
            self.scroller = ScrollerBox(self, instance_index)
            self.scroller_stack.add_named(self.scroller, key)

            plugin = PluginSearch(set_headerbar_color = self.set_headerbar_color,
                                  add_result = self.scroller.add_result,
                                  hide_scroller_error_box = self.scroller.hide_scroller_error_box,
                                  show_scroller_error_box = self.scroller.show_scroller_error_box)
            plugin.do_search(query = search_query)

    def set_headerbar_color(self):
        self.get_visible_scroller()
        self.navigation_previous.set_sensitive(True)
        self.navigation_next.set_sensitive(True)
        nav_current_context = self.navigation_current.get_style_context()
        css_classes = nav_current_context.list_classes()
        for css_class in css_classes:
            if css_class.startswith('color'):
                nav_current_context.remove_class(css_class)

        if self.scroller_index < 8:
            nav_current_context.add_class("color" + str(self.scroller_index))

    def get_visible_scroller(self):
        visible_scroller = self.scroller_stack.get_visible_child_name()
        self.scroller_index = self.stacks_list.index(visible_scroller)

    @Gtk.Template.Callback()
    def show_previous_results(self, button):
        self.get_visible_scroller()
        if self.scroller_index > 0:
            previous_name = self.stacks_list[self.scroller_index-1]
            previous_scroller = self.scroller_stack.get_child_by_name(str(previous_name))
            self.scroller_stack.set_visible_child(previous_scroller)
            self.set_headerbar_color()

    @Gtk.Template.Callback()
    def show_next_results(self, button):
        self.get_visible_scroller()
        if self.scroller_index < len(self.scroller_stack) - 1:
            next_name = self.stacks_list[self.scroller_index+1]
            next_scroller = self.scroller_stack.get_child_by_name(str(next_name))
            self.scroller_stack.set_visible_child(next_scroller)
            self.set_headerbar_color()

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

    @Gtk.Template.Callback()
    def keypress_listener(self, widget, ev):
        key = Gdk.keyval_name(ev.keyval)
        if self.scroller_stack:
            visible_scroller = self.scroller_stack.get_visible_child()
            if visible_scroller:
                focus_child = visible_scroller.results_list.get_focus_child()
                if focus_child:
                    if key == "Escape":
                        focus_child.get_child().unfullscreen_button(None)
                    if key == "space":
                        self.play_pause_toggle(focus_child)
                    if key == "f":
                        self.fullscreen_toggle(focus_child)

    def pause_all(self):
        if self.scroller_stack:
            scrollers = self.scroller_stack.get_children()
            for scroller in scrollers:
                flowboxes = scroller.results_list.get_children()
                for flowbox in flowboxes:
                    flowbox.get_child().null_out_player()

    def inhibit_app(self):
        self.application.inhibit(self,
                Gtk.ApplicationInhibitFlags.IDLE |
                Gtk.ApplicationInhibitFlags.LOGOUT,
                "Stream-ing Video")

    def uninhibit_app(self):
        self.application.inhibit(self,
                Gtk.ApplicationInhibitFlags.IDLE |
                Gtk.ApplicationInhibitFlags.LOGOUT,
                "Stream-ing Video")

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
        self.application = kwargs.get('application', None)

        self.is_playing = False
        self.is_fullscreen = False
        self.strong_instances = []
        instances = Instances(app_window = self)
        instances.get_strong_instances()

        menu = Menu(app_window = self)
        self.menu_button.set_popover(menu)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/sm/puri/Stream/ui/stream.css')
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
