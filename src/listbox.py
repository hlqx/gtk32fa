# listbox.py
#
# Copyright 2020 Niall Asher
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>
from gi.repository import Gtk

class TwoFactorListBoxRow(Gtk.ListBoxRow):
    def __init__(self):
        # create widgets
        Gtk.ListBoxRow.__init__(self)
        self.row = self
        self.stack = Gtk.Stack()
        self.stack.set_homogeneous(False)
        self.stack.set_interpolate_size(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.row_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row_vbox_2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        normal_btn_layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        edit_btn_layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        authentication_code_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        increment_code_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        copy_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU)
        inc_icon = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
        for _, icon_name in enumerate([copy_icon, inc_icon]):
            icon_name.get_style_context().add_class("button_icon")
        self.name_label = Gtk.Label(xalign=0)
        self.issuer_label = Gtk.Label(xalign=0)
        self.issuer_label.get_style_context().add_class("italiclbl")
        #self.copy_button.set_relief(Gtk.ReliefStyle.NONE)
        self.increment_counter_button = Gtk.Button()
        self.copy_button = Gtk.Button()
        # the code_button class removes padding around the object
        #self.increment_counter_button.get_style_context().add_class("code_button")
        self.increment_counter_button.set_relief(Gtk.ReliefStyle.NONE)
        self.authentication_code_label = Gtk.Label(xalign=0)
        self.copy_button.set_relief(Gtk.ReliefStyle.NONE)
        # add the custom authentication_code css class to the authentication code label
        self.authentication_code_label.get_style_context().add_class("authentication_code")
        self.copy_button.add(authentication_code_hbox)
        authentication_code_hbox.pack_start(copy_icon, False, False, 3)
        authentication_code_hbox.pack_end(self.authentication_code_label, False, False, 3)
        self.copy_button.get_style_context().add_class("code_button")
        self.counter_label = Gtk.Label(xalign=1)
        self.increment_counter_button.add(increment_code_hbox)
        increment_code_hbox.pack_start(inc_icon, False, False, 3)
        increment_code_hbox.pack_end(self.counter_label, False, False, 3)
        self.delete_button = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
        self.edit_button = Gtk.Button.new_from_icon_name("edit-select-all", Gtk.IconSize.BUTTON)
        self.move_up_button = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        self.move_down_button = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        for _, name in enumerate([self.delete_button, self.edit_button, self.move_up_button, self.move_down_button]):
            name.get_style_context().add_class("circular")
        # packing main boxes
        self.row_hbox.pack_start(row_vbox, False, True, 6)
        self.row_hbox.pack_end(row_vbox_2, False, True, 6)
        row_vbox_2.set_center_widget(self.stack)
        # packing
        row_vbox.pack_start(self.name_label, True, True, 6)
        row_vbox.pack_end(self.issuer_label, True, True, 6)
        normal_btn_layout.pack_start(self.increment_counter_button, False, False, 3)
        normal_btn_layout.pack_start(self.copy_button, False, False, 0)
        edit_btn_layout.pack_start(self.move_up_button, False, False, 3)
        edit_btn_layout.pack_start(self.move_down_button, False, False, 3)
        edit_btn_layout.pack_start(self.edit_button, False, False, 3)
        edit_btn_layout.pack_start(self.delete_button, False, False, 3)
        # add stack pages
        self.stack.add_named(normal_btn_layout, "s1")
        self.stack.add_named(edit_btn_layout, "s2")
        # finishing touch
        self.row.add(self.row_hbox)
        self.show_all()

class EmptyListWidget(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        empty_list_label = Gtk.Label(label="There doesn't seem to be anything here.")
        empty_list_label.set_markup('<span style="normal" size="large">There doesn\'t seem to anything here.</span>\n'
                                    'Try adding something to the list using the + button.')
        self.set_center_widget(vbox)
        vbox.pack_start(empty_list_label, True, True, 6)
        self.show_all()
