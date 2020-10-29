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

from pyotp import TOTP, HOTP
from uuid import uuid4

class TwoFactorCode:

    def __init__(self, name, issuer, codetype, codestr, counter, pos, ui):
        # generate the uuid used as the dict key later
        # we want this to be a string
        self.uuid = uuid4().__str__()
        # grab values from call
        self.name = name
        self.issuer = issuer
        self.codetype = codetype
        self.codestr = codestr
        self.ui = ui
        self.counter = counter
        self.pos = pos
        # check code type, make code object for type,
        # or throw exception if not recognized
        if codetype == 'totp':
            self.code = TOTP(self.codestr)
            self.curcode = self.code.now()
        elif codetype == 'hotp':
            self.code = HOTP(self.codestr)
            self.curcode = self.code.at(self.counter)
        else:
            raise TypeError('codetype was not hotp or totp')

    def set_counter(self, value):
        # set the counter to a specified value
        if self.counter is not None:
            self.counter = value.__int__()

    def get_current_code(self):
        # return current code (plaintext)
        if self.codetype == 'totp':
            return self.code.now().__str__()
        elif self.codetype == 'hotp':
            return self.code.at(self.counter).__str__()

class TwoFactorUIElements():

        def __init__(self, stack, authlbl, issuerlbl, namelbl, row, rowhbox, counterlbl=None):
            self.stack = stack
            self.authlbl = authlbl
            self.issuerlbl = issuerlbl
            self.namelbl = namelbl
            self.row = row
            self.rowhbox = rowhbox
            self.counterlbl = counterlbl

        def enable_editmode(self, enable: bool):
            if enable:
                self.stack.set_visible_child_name("s2")
            else:
                self.stack.set_visible_child_name("s1")
