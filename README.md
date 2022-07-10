# GIGABYTE Aero laptop keyboard RGB control

## See also

* This is derived from [Martin Koppehel’s C utility][martin31821] based on libusb.
  The issue with libusb is that you have to detach the device,
  and that leads to a window of time when your keyboard does not accept key presses.

* @gillaumesalagnac has a [fork](gillaumesalagnac) of Martin’s utility
  adding a web UI tool for making custom profiles.

* Paul Ridgway [describes](blockdev) his adventures reverse-engineering a different model
  and [publishes](paul-ridgway) a Ruby-based utility.

* [libhidapi][], [Python bindings][pip-hidapi], [Ubuntu package][ubuntu-hidapi]

  libhidapi-hidraw specifically allows access to the device without detaching.

[martin31821]: https://github.com/martin31821/fusion-kbd-controller/
[gillaumesalagnac]: https://github.com/guillaumesalagnac/fusion-kbd-controller/
[blockdev]: https://blockdev.io/gigabyte-aero-w15-keyboard-and-linux-ubuntu/
[paul-ridgway]: https://github.com/paul-ridgway/aero-keyboard/
[libhidapi]: https://github.com/libusb/hidapi/
[pip-hidapi]: https://pypi.org/project/hidapi/
[ubuntu-hidapi]: https://packages.ubuntu.com/search?keywords=python3-hidapi&searchon=names&suite=all&section=all


## Usage

Add yourself to the `plugdev` group, put `<50-hidraw.rules>` into `/etc/udev/rules.d` and reboot.
Check with `ls -al /dev/hidraw*` that the hidraw devices are owned by root:plugdev.
Check with `groups` that you are in the `plugdev` group.

For starters, try `./aero_keyboard.py preset --mode breathing --color green --speed 5 --brightness 20`.

For recognized modes and colors, please read the script.

Custom static color maps can be uploaded with `./aero_keyboard.py custom --file <filename>`.
The file must be 512 bytes long.
You can generate one with gillaumesalagnac’s tool.

Alternatively, use `aero_keyboard.py` as a library.
Instantiate an `AeroKeyboard` object and call its `set_preset` or `set_custom` methods.
A `bytes` buffer for `set_custom` can be generated with the `pack_rgb` function
which accepts a dictionary from key names to RGB tuples.


## License

MIT.
