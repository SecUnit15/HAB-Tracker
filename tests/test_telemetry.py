"""Tests for building the message and reading the modem's replies.

Run from the repo root:  python3 -m unittest discover -s tests
"""

import unittest

import hardware_stubs  # noqa: F401  (must come first - sets up the import path)

import telemetry


class BuildMessage(unittest.TestCase):
    def test_normal_reading(self):
        self.assertEqual(
            telemetry.build_message(3, 417, 33.1294, -116.3245, 17917, 14, 3.98, -18, 2),
            "H2|3|417|33.1294|-116.3245|17917|14|3.98|-18|2",
        )

    def test_starts_with_the_version_marker(self):
        # The ground uses this to tell H2 from the 2025 six-field format.
        msg = telemetry.build_message(1, 1, 0.0, 0.0, 0, 0, 0.0, 0, 0)
        self.assertTrue(msg.startswith("H2|"))

    def test_missing_readings_become_question_marks(self):
        # Not 0 - zero is a real value for altitude, satellites and temperature.
        self.assertEqual(
            telemetry.build_message(3, 418, None, None, 17920, None, 3.97, -18, None),
            "H2|3|418|?|?|17920|?|3.97|-18|?",
        )

    def test_a_zero_reading_is_not_confused_with_a_missing_one(self):
        msg = telemetry.build_message(0, 0, 0.0, 0.0, 0, 0, 0.0, 0, 0)
        self.assertNotIn("?", msg)

    def test_everything_missing_still_builds(self):
        # The old code crashed here: f"{None:.4f}" raises.
        msg = telemetry.build_message(None, None, None, None, None, None, None, None, None)
        self.assertEqual(msg, "H2|?|?|?|?|?|?|?|?|?")

    def test_fits_in_one_iridium_message(self):
        biggest = telemetry.build_message(
            255, 65535, -33.1294, -116.3245, 99999, 24, 4.25, -99, 99999
        )
        self.assertLess(len(biggest), 340)


class ParseSbdix(unittest.TestCase):
    def test_reads_all_six_fields(self):
        self.assertEqual(
            telemetry.parse_sbdix("+SBDIX: 0, 1234, 0, 0, 0, 0"),
            {'mo_status': 0, 'momsn': 1234, 'mt_status': 0,
             'mtmsn': 0, 'mt_length': 0, 'mt_queued': 0},
        )

    def test_keeps_the_momsn(self):
        # This is the field that tells the ground a resend from a new reading.
        self.assertEqual(telemetry.parse_sbdix("+SBDIX: 2, 987, 0, 0, 0, 0")['momsn'], 987)

    def test_ignores_other_lines(self):
        self.assertIsNone(telemetry.parse_sbdix("OK"))
        self.assertIsNone(telemetry.parse_sbdix("+CSQ: 4"))

    def test_rejects_a_truncated_reply(self):
        self.assertIsNone(telemetry.parse_sbdix("+SBDIX: 0, 1234"))

    def test_rejects_garbled_numbers(self):
        self.assertIsNone(telemetry.parse_sbdix("+SBDIX: 0, ??, 0, 0, 0, 0"))


class IsDelivered(unittest.TestCase):
    def test_zero_to_four_are_delivered(self):
        for status in (0, 1, 2, 3, 4):
            self.assertTrue(telemetry.is_delivered(status), status)

    def test_five_to_eight_are_failures(self):
        # The 2025 bug: these were accepted as success, so the retry was
        # skipped and the reading was lost while the log said it had sent.
        for status in (5, 6, 7, 8):
            self.assertFalse(telemetry.is_delivered(status), status)

    def test_later_errors_are_failures(self):
        for status in (10, 13, 14, 15, 32, 38):
            self.assertFalse(telemetry.is_delivered(status), status)


class OutboxHasMessage(unittest.TestCase):
    def test_flag_one_means_waiting(self):
        self.assertTrue(telemetry.outbox_has_message("+SBDS: 1, 5, 0, -1"))

    def test_flag_zero_means_empty(self):
        self.assertFalse(telemetry.outbox_has_message("+SBDS: 0, 5, 0, -1"))

    def test_ignores_other_lines(self):
        self.assertIsNone(telemetry.outbox_has_message("OK"))


if __name__ == "__main__":
    unittest.main()
