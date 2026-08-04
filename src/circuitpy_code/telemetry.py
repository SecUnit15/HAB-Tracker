"""Building the telemetry message and reading the modem's replies.

Nothing in here touches hardware, so it can be imported and tested with plain
Python on a laptop. Keep it that way: no `board`, `busio` or `time` imports.
"""


PAYLOAD_VERSION = "H2"


def format_field(value, style="%d"):
    """Format one reading, or '?' if we do not have it."""
    if value is None:
        return "?"
    return style % value


def build_message(boot_id, sequence, lat, lon, altitude, satellites,
                  battery, temperature, fix_age_s):
    """Build the pipe-separated message we send over Iridium.

    H2|boot|seq|lat|lon|altitude_m|satellites|battery_v|temperature_f|fix_age_s

    boot counts restarts and seq counts messages, so the ground can tell a
    resent message (the same seq arriving twice) apart from a new reading that
    happens to look identical. A reading we do not have is sent as "?" rather
    than a fake 0, because 0 is a real value for several of these fields.
    """
    return "|".join([
        PAYLOAD_VERSION,
        format_field(boot_id),
        format_field(sequence),
        format_field(lat, "%.4f"),
        format_field(lon, "%.4f"),
        format_field(altitude),
        format_field(satellites),
        format_field(battery, "%.2f"),
        format_field(temperature),
        format_field(fix_age_s),
    ])


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
