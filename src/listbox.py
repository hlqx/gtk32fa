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

from gi.repository import Gtk, GdkPixbuf, Gdk
from gi.repository.Handy import Avatar



class TwoFactorListBoxRow(Gtk.ListBoxRow):

        # TODO: go against base instinct and replace the camelCase
        def __init__(self, uuid: str) -> Gtk.ListBoxRow:
            # initialize the listboxrow
            Gtk.ListBoxRow.__init__(self)
            self.row = self
            # uuid
            self.uuid = uuid
            # main layout box
            self.mainLayout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            # sublayouts
            self.infoLayout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
            self.ctrlLayout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            self.detailLayout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            self.issuerAndCounterLayout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            # buttonbox for copy & increment
            buttonBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            #buttonBox.set_layout(Gtk.ButtonBoxStyle.END)
            buttonBox.set_margin_top(18)
            buttonBox.set_margin_bottom(18)
            buttonBox.get_style_context().add_class("linked")
            # create icons for buttons & apply css class
            copyIcon = Gtk.Image.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU)
            incrementIcon = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
            for _, iconName in enumerate([copyIcon, incrementIcon]):
                iconName.get_style_context().add_class("button_icon")
            incrementIcon.set_margin_left(2)
            # create avatar
            self.avatar = Avatar()
            self.avatar.set_size(64)
            self.avatar.get_style_context().add_class("avatar-main")
            self.avatar.set_show_initials(True)
            # create widgets
            self.nameLabel = Gtk.Label(xalign=0)
            self.issuerLabel = Gtk.Label(xalign=0)
            self.issuerLabel.get_style_context().add_class("italiclbl")
            self.authCodeLabel = Gtk.Label(xalign=0)
            self.authCodeLabel.get_style_context().add_class("authentication_code")
            self.incrementCounterLabel = Gtk.Label(xalign=0)
            self.incrementCounterLabel.get_style_context().add_class("italiclbl")
            self.incrementCounterButton = Gtk.Button()
            self.copyButton = Gtk.Button()
            # remove relief on copy & increment buttons; makes them blend in
            self.incrementCounterButton.set_relief(Gtk.ReliefStyle.NONE)
            self.copyButton.set_relief(Gtk.ReliefStyle.NONE)
            # button layouts
            self.authCodeLayout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            self.incrementCodeLayout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            # pack widgets into button layouts & add them to the buttons
            self.authCodeLayout.pack_start(copyIcon, False, False, 3)
            self.authCodeLayout.pack_end(self.authCodeLabel, False, False, 3)
            self.copyButton.add(self.authCodeLayout)
            self.incrementCounterButton.add(incrementIcon)
            # add style class to copyButton
            self.copyButton.get_style_context().add_class("code_button")
            # create action buttons
            self.deleteButton = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
            self.editButton = Gtk.Button.new_from_icon_name("edit-select-all", Gtk.IconSize.BUTTON)
            for _, button in enumerate([self.deleteButton, self.editButton]):
                button.get_style_context().add_class("circular")
                button.set_margin_top(5)
                button.set_margin_bottom(5)
            # margins
            self.nameLabel.set_margin_top(7)
            self.issuerLabel.set_margin_bottom(7)
            self.incrementCounterLabel.set_margin_bottom(7)
            # seperator for issuer & counter
            self.seperator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            self.seperator.set_margin_bottom(7)
            self.seperator.set_margin_left(2)
            # pack detail layout
            self.detailLayout.pack_start(self.nameLabel, False, False, 4)
            self.detailLayout.pack_end(self.issuerAndCounterLayout, False, False, 4)
            self.issuerAndCounterLayout.pack_start(self.issuerLabel, False, False, 0)
            self.issuerAndCounterLayout.pack_start(self.seperator, False, False, 4)
            self.issuerAndCounterLayout.pack_start(self.incrementCounterLabel, False, False, 0)
            # pack info layout
            self.infoLayout.pack_start(self.avatar, False, False, 3)
            self.infoLayout.pack_start(self.detailLayout, False, False, 3)
            self.infoLayout.pack_end(buttonBox, False, False, 3)
            buttonBox.pack_start(self.incrementCounterButton, False, False, 0)
            buttonBox.pack_start(self.copyButton, False, False, 0)
            # pack ctrlLayout
            self.ctrlLayout.pack_end(self.editButton, False, False, 3)
            self.ctrlLayout.pack_end(self.deleteButton, False, False, 3)
            # create revealer for second row
            self.revealer = Gtk.Revealer()
            self.revealer.set_reveal_child(False)
            self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
            self.revealer.set_transition_duration(500)
            # add revealer
            self.revealer.add(self.ctrlLayout)
            # create vertical sizegroup for infoLayout buttons
            sizegroup = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
            sizegroup.add_widget(self.incrementCounterButton)
            sizegroup.add_widget(self.copyButton)
            # pack main layout
            self.mainLayout.pack_start(self.infoLayout, True, True, 2)
            self.mainLayout.pack_end(self.revealer, False, True, 2)
            # create drag handle & add to control
            self.handle = Gtk.Button()
            self.handle.get_style_context().add_class("circular")
            self.handle.get_style_context().add_class("")
            self.handle.add(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
            self.ctrlLayout.pack_start(self.handle, False, False, 3)
            # make main layout a hoverbox
            self.mainLayout.get_style_context().add_class("hoverbox")
            # add main layout to row
            self.row.add(self.mainLayout)
            self.row.get_style_context().add_class("codelistbox")
            self.show_all()
