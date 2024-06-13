# SPDX-FileCopyrightText: 2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import os
import psutil
import socket
import logging
import sys
import time
import usb.core

from seguro.common import broker, config


def strip_none(d: dict) -> dict:
    """Remove elements from dictionary whose value is None

    Args:
      d: The dictionary from which None values should be removed

    Returns:
      The filtered dictionary

    """
    return {k: v for k, v in d.items() if v is not None}


def get_nix() -> dict:
    nix = {}

    if os.stat("/var/run/current-system"):
        nix["current_system"] = os.readlink("/var/run/current-system")

    return nix


def get_disks() -> list[dict]:
    disks = [p._asdict() for p in psutil.disk_partitions()]
    for disk in disks:
        disk["opts"] = disk["opts"].split(",")
        try:
            disk["usage"] = psutil.disk_usage(disk["mountpoint"])._asdict()
        except Exception:
            pass

    return disks


def get_usb() -> list:
    devs = []
    for cfg in usb.core.find(find_all=True):
        dev = {
            "vendor_id": cfg.idVendor,
            "product_id": cfg.idProduct,
        }

        m = {
            "product": cfg.iProduct,
            "serial_no": cfg.iSerialNumber,
            "manufacturer": cfg.iManufacturer,
        }

        for k, v in m.items():
            try:
                dev[k] = usb.util.get_string(cfg, v)
            except ValueError:
                pass

        devs.append(dev)

    return devs


def get_nics() -> dict:
    nic_addrs = psutil.net_if_addrs()
    nic_stats = psutil.net_if_stats()
    nics = {}
    for name, ctr in psutil.net_io_counters(pernic=True).items():
        nics[name] = ctr._asdict()

        stats = nic_stats[name]._asdict()

        del stats["isup"]
        stats["flags"] = stats["flags"].split(",")

        nics[name]["statistics"] = stats
        nics[name]["addresses"] = [
            strip_none(a._asdict()) for a in nic_addrs[name]
        ]

    return nics


def get_sensors() -> dict:
    sensors = {}

    if fans := psutil.sensors_fans():
        sensors["fan"] = {
            name: [strip_none(fan._asdict()) for fan in fans]
            for name, fans in fans.items()
        }

    if temps := psutil.sensors_temperatures():
        sensors["temp"] = {
            name: [strip_none(temp._asdict()) for temp in temps]
            for name, temps in temps.items()
        }

    if batts := psutil.sensors_battery():
        sensors["battery"] = {
            name: [strip_none(batt._asdict()) for batt in batts]
            for name, batts in batts.items()
        }

    return sensors


def get_status() -> dict:

    freq = psutil.cpu_freq()
    uname = os.uname()
    proc = psutil.Process()

    with proc.oneshot():

        return {
            "boottime": psutil.boot_time(),
            "processes": len(psutil.pids()),
            "usb": get_usb(),
            "uptime": {
                "process": time.time() - proc.create_time(),
                "system": time.time() - psutil.boot_time(),
            },
            "host": socket.getfqdn(),
            "kernel": {
                "sysname": uname.sysname,
                "nodename": uname.nodename,
                "release": uname.release,
                "version": uname.version,
                "machine": uname.machine,
            },
            "cpu": {
                "cores": {
                    "physical": psutil.cpu_count(logical=False),
                    "logical": psutil.cpu_count(logical=True),
                },
                "usage": psutil.cpu_percent(interval=1),
                "loadavg": psutil.getloadavg(),
                "frequency": freq._asdict() if freq else {},
                "times": psutil.cpu_times()._asdict(),
                "stats": psutil.cpu_stats()._asdict(),
            },
            "memory": psutil.virtual_memory()._asdict(),
            "swap": psutil.swap_memory()._asdict(),
            "users": [u._asdict() for u in psutil.users()],
            "disks": get_disks(),
            "nics": get_nics(),
            "sensors": get_sensors(),
            "nix": get_nix(),
        }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--topic", type=str, default="heartbeats")
    parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    b = broker.Client("heartbeat")
    msg_info = b.publish(args.topic, json.dumps(get_status()))
    msg_info.wait_for_publish(10)

    return 0


if __name__ == "__main__":
    sys.exit(main())
