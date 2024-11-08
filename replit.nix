{pkgs}: {
  deps = [
    pkgs.harfbuzz
    pkgs.cairo
    pkgs.pango
    pkgs.gtk3
    pkgs.bluez-tools
    pkgs.dbus
    pkgs.libxcrypt
    pkgs.bluez
  ];
}
