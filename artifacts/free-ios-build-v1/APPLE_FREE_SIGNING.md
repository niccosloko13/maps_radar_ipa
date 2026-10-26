# Apple free signing

Simulator compilation/run does not need device signing. Device code can be compiled with `CODE_SIGNING_ALLOWED=NO`, but a physical iPhone accepts only an app signed and provisioned for it.

An Apple ID Personal Team may enable direct development installation through interactive Xcode on a Mac. It is not automatable safely in this CI configuration: no Apple ID, password, 2FA code, certificate or profile is requested/stored. Therefore the honest state after a successful unsigned CI compile would be `BUILD_OK` + `SIGNING_BLOCKED_PERSONAL_TEAM` / `PERSONAL_TEAM_REQUIRES_XCODE_INTERACTION`.

No IPA is fabricated. `export-ipa.sh` emits `SIGNING_REQUIRED` unless a real valid signing identity and archive are already present.
