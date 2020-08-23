# GTK32FA
## 2 Factor Authentication Wallet
---
A 2 factor authentication program for GTK3.
Might work on platforms other than Linux, but currently uses XDG for data storage, so you might have to set some environment variables with the same names for it to function.

Check the projects tab for feature plans.

Notes:
- To clear database (if you want to change encryption, or it's corrupted etc.) delete $XDG_CONFIG_HOME/GTK32FA/config.yaml
- Currently only supports TOTP codes
- HOTP support is planned but not currently a priority
- Editing a code does not retain it's position in the list (looking at fixing soon)
- Cannot sort or group codes, they're just in the order they're in (looking at fixing relatively soon)

Ext module dependencies:
- pygobject
- xdg
- pyotp
- pyyaml
- cryptography
