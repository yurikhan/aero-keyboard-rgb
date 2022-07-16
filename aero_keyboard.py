#!/usr/bin/python3

import argparse
from argparse import ArgumentParser
from enum import Enum, IntEnum
from functools import wraps
from pathlib import Path
import struct
from time import sleep
from typing import Callable, Dict, List, Literal, NamedTuple, Optional, Type, TypeVar, cast


class Kind(IntEnum):
    preset = 0x8
    read_config = 0x92
    custom_config = 0x12


class Mode(IntEnum):
    static = 1
    breathing = 2
    # wave = 3  # do not use — buggy
    fade_on_keypress = 4
    marquee = 5
    ripple = 6
    flash_on_keypress = 7
    neon = 8
    rainbow_marquee = 9
    raindrop = 10
    circle_marquee = 11
    hedge = 12
    rotate = 13
    custom = 0x34


class Color(IntEnum):
    black = 0
    red = 1
    green = 2
    yellow = 3
    blue = 4
    orange = 5
    purple = 6
    white = 7


class Report(NamedTuple):
    kind: Kind
    mode: Mode
    speed_length: int  # max 10, 1 fastest
    brightness: int    # max 51
    color: Color
    reserved2: Literal[0, 1]

    def __bytes__(self) -> bytes:
        result = struct.pack('BBBBBBBB', self.kind, 0, self.mode, self.speed_length,
                             self.brightness, self.color, self.reserved2, self.checksum())
        return result

    def checksum(self) -> int:
        return (0xFF - (self.kind + self.mode + self.speed_length
                        + self.brightness + self.color + self.reserved2) & 0xFF)


class AeroKeyboard:
    def __init__(self, vendor_id: int = 0x1044, product_id: int = 0x7a3b) -> None:
        import hidapi  # type: ignore
        # HACKERY: hidapi imports hidapi-libusb first,
        # and we’d like to avoid that
        # because that one unbinds devices when they are opened.
        hidapi.hidapi.hid_exit()
        hidapi.hidapi = hidapi.ffi.dlopen('hidapi-hidraw')
        if hidapi.hidapi.hid_init() == -1:
            raise OSError('Failed to initialize hidapi')

        devinfo = next((di for di in hidapi.enumerate()
                        if di.vendor_id == vendor_id
                        and di.product_id == product_id
                        and di.interface_number == 3), None)

        if not devinfo:
            raise Exception(f'Device {vendor_id:04x}:{product_id:04x} interface 3 not found')

        self._device = hidapi.Device(devinfo)

    def set_preset(self, mode: Mode, speed: int, brightness: int, color: Color) -> None:
        self._device.send_feature_report(bytes(Report(
            Kind.preset, mode, speed, brightness, color, 0)), b'\0')

    def set_custom(self, data: bytes) -> None:
        assert len(data) == 512
        self._device.send_feature_report(bytes(Report(
            Kind.custom_config, Mode.static, 8, 0, Color.black, 0)), b'\0')
        for i in range(8):
            self._device.write(data[i*64 : i*64 + 64])
        self._device.send_feature_report(bytes(Report(
            Kind.preset, Mode.custom, 5, 50, Color.green, 1)), b'\0')


KeyName = str


KEYS: List[Optional[KeyName]] = [
    None,     None,     None,    None,  None,   None,    # 1/6
    'lctrl',  'lshift', 'caps',  'tab', '`',    'esc',   # 7/12
    'fn',     'iso',    'a',     'q',   '1',    'f1',    # 13/18
    'gui',    'z',      's',     'w',   '2',    'f2',    # 19/24
    'lalt',   'x',      'd',     'e',   '3',    'f3',    # 25/30
    None,     'c',      'f',     'r',   '4',    'f4',    # 31/36
    None,     'v',      'g',     't',   '5',    'f5',    # 37/42
    'space',  'b',      'h',     'y',   '6',    'f6',    # 43/48
    None,     'n',      'j',     'u',   '7',    'f7',    # 49/54
    None,     'm',      'k',     'i',   '8',    'f8',    # 55/60
    'ralt',   ',',      'l',     'o',   '9',    'f9',    # 61/66
    'app',    '.',      ';',     'p',   '0',    'f10',   # 67/72
    'rctrl',  '/',      "'",     '[',   '-',    'f11',   # 73/78
    None,     None,     None,    ']',   '=',    'f12',   # 79/84
    'left',   'rshift', '\\',    None,  None,   'pause', # 85/90
    'down',   'up',     'enter', None,  'bksp', 'del',   # 91/96
    'right',  'k1',     'k4',    'k7',  'num',  'home',  # 97/102
    'k0',     'k2',     'k5',    'k8',  'k/',   'pgup',  # 103/108
    'k.',     'k3',     'k6',    'k9',  'k*',   'pgdn',  # 109/114
    'kenter', None,     'k+',    None,  'k-',   'end',   # 115/120
    None, None, None, None, None, None, None, None,      # 121/128
]


class RGB(NamedTuple):
    r: int
    g: int
    b: int

    def __bytes__(self) -> bytes:
        return struct.pack('BBBB', 0, self.r, self.g, self.b)

    @classmethod
    def from_hex(cls, s: str) -> 'RGB':
        if s.startswith('#'):
            s = s[1:]
        return cls(r=int(s[:2], 16), g=int(s[2:4], 16), b=int(s[4:], 16))


def pack_rgb(data: Dict[KeyName, RGB]) -> bytes:
    return b''.join(bytes(cast(Dict[Optional[KeyName], RGB], data).get(k, b'\0\0\0\0'))
                    for k in KEYS)


T = TypeVar('T', bound=IntEnum)


def parse_enum(enum: Type[T]) -> Callable[[str], T]:
    @wraps(enum)
    def _do_parse(s: str) -> T:
        try:
            return enum[s]
        except KeyError as e:
            raise ValueError(f'{e}') from e

    return _do_parse


def speed(s: str) -> int:
    result = int(s)
    if 0 <= result <= 10:
        return result
    raise ValueError


def brightness(s: str) -> int:
    result = int(s)
    if 0 <= result <= 51:
        return result
    raise ValueError


def parse_args() -> argparse.Namespace:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    preset_parser = subparsers.add_parser('preset')
    preset_parser.set_defaults(handler=handle_preset)
    preset_parser.add_argument('--mode', '-m', type=parse_enum(Mode), required=True)
    preset_parser.add_argument('--speed', '-s', type=speed, default=0)
    preset_parser.add_argument('--brightness', '-b', type=brightness, default=20)
    preset_parser.add_argument('--color', '-c', type=parse_enum(Color), default=Color.white)

    custom_parser = subparsers.add_parser('custom')
    custom_parser.set_defaults(handler=handle_custom)
    custom_parser.add_argument('file', type=Path)

    return parser.parse_args()


def handle_preset(args: argparse.Namespace) -> None:
    keyboard = AeroKeyboard()
    keyboard.set_preset(args.mode, args.speed, args.brightness, args.color)


def handle_custom(args: argparse.Namespace) -> None:
    keyboard = AeroKeyboard()
    keyboard.set_custom(args.file.read_bytes())


def main() -> None:
    args = parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
