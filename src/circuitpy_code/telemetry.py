"""Building the telemetry message and reading the modem's replies.

Nothing in here touches hardware, so it can be imported and tested with plain
Python on a laptop. Keep it that way: no `board`, `busio` or `time` imports.
"""


def build_message(lat, lon, altitude, satellites, battery, temperature):
    """Build the pipe-separated message we send over Iridium.

    Format: lat|lon|altitude_m|satellites|battery_v|temperature_f
    """
    return "%.4f|%.4f|%d|%s|%.1f|%.0f" % (
        lat, lon, altitude or 0, satellites, battery or 0, temperature or 0
    )


def parse_sbdix(line):
    """Read a +SBDIX reply into a dict, or None if this is not one.

    Format: +SBDIX: <MO status>,<MOMSN>,<MT status>,<MTMSN>,<MT len>,<MT queued>
    """
    if "+SBDIX:" not in line:
        return None

    try:
        fields = [int(v) for v in line.split(":")[1].split(",")]
    except (ValueError, IndexError):
        return None

    if len(fields) != 6:
        return None

    return {
        'mo_status': fields[0],
        'momsn': fields[1],
        'mt_status': fields[2],
        'mtmsn': fields[3],
        'mt_length': fields[4],
        'mt_queued': fields[5],
    }


def is_delivered(mo_status):
    """Iridium reports 0-4 for a delivered message and 5 upwards for failure."""
    return 0 <= mo_status <= 4


def outbox_has_message(line):
    """Read a +SBDS reply and say whether a message is waiting to go out.

    Format: +SBDS: <outbox flag>,<MOMSN>,<inbox flag>,<MTMSN>
    """
    if "+SBDS:" not in line:
        return None

    try:
        return int(line.split(":")[1].split(",")[0]) == 1
    except (ValueError, IndexError):
        return None
