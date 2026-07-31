"""Tests for the send sequence, using a pretend modem instead of hardware.

The question these answer: can the same reading ever reach the satellite twice?
That is what appears to have happened on the 2025 flight, where 60 of 99 stored
reports were exact copies of the one before.

Run from the repo root:  python3 -m unittest discover -s tests
"""

import unittest

import hardware_stubs  # noqa: F401  (must come first - sets up the import path)

import rockblock_module


class FakeModem:
    """A pretend RockBLOCK on the other end of the serial line.

    It keeps an outbox like the real one does, and records every message that
    actually reached the satellite in `sent`.
    """

    def __init__(self):
        self.outbox = None
        self.sent = []
        self.commands = []
        self.next_momsn = 100
        self.fail_next_write = False
        # The nastier case: the write is answered with OK but never lands.
        # A late reply from the previous session is enough to cause this.
        self.write_silently_fails = False
        self._pending = []

    # -- the bits the flight code calls -------------------------------------

    def reset_input_buffer(self):
        pass

    def write(self, data):
        command = data.decode().strip()
        self.commands.append(command)
        self._pending.extend(self._reply_to(command))

    def readline(self):
        if not self._pending:
            return None
        return (self._pending.pop(0) + "\r\n").encode()

    # -- pretend modem behaviour --------------------------------------------

    def _reply_to(self, command):
        if command == "AT+SBDD0":
            self.outbox = None
            return ["OK"]

        if command.startswith("AT+SBDWT="):
            if self.fail_next_write:
                self.fail_next_write = False
                return ["ERROR"]
            if self.write_silently_fails:
                return ["OK"]  # answered, but the outbox is untouched
            self.outbox = command[len("AT+SBDWT="):]
            return ["OK"]

        if command == "AT+SBDS":
            flag = 1 if self.outbox else 0
            return ["+SBDS: %d, 0, 0, -1" % flag, "OK"]

        if command == "AT+SBDIX":
            if self.outbox is None:
                # Nothing to send: the real modem reports a failed session.
                return ["+SBDIX: 32, 0, 0, 0, 0, 0", "OK"]
            self.sent.append(self.outbox)
            self.next_momsn += 1
            return ["+SBDIX: 0, %d, 0, 0, 0, 0" % self.next_momsn, "OK"]

        if command == "AT+CGSN":
            return ["300434061666900", "OK"]

        return ["OK"]


READING_A = (1, 1, 33.1294, -116.3245, 17917, 14, 3.98, -18, 2)
READING_B = (1, 2, 33.1301, -116.3260, 18120, 14, 3.97, -19, 2)


class SendSequence(unittest.TestCase):
    def setUp(self):
        # The real code sleeps while settling and between retries.
        self._real_sleep = rockblock_module.time.sleep
        rockblock_module.time.sleep = lambda _seconds: None

        self.modem = FakeModem()
        self.radio = rockblock_module.SimpleRockBLOCK(debug=False, uart=self.modem)

    def tearDown(self):
        rockblock_module.time.sleep = self._real_sleep

    def test_a_normal_send_delivers_exactly_one_message(self):
        ok, _ = self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        self.assertTrue(ok)
        self.assertEqual(len(self.modem.sent), 1)

    def test_two_sends_deliver_two_different_messages(self):
        self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        self.radio.send_tracking_data_with_retry(*READING_B, max_attempts=2)
        self.assertEqual(len(self.modem.sent), 2)
        self.assertNotEqual(self.modem.sent[0], self.modem.sent[1])

    def test_a_silently_failed_write_does_not_start_a_session(self):
        """The 2025 failure, as a test.

        A write can be answered with OK without actually landing - a late reply
        from the previous session is enough to fool the reader. When that
        happens we must not start a session, because whatever is sitting in the
        outbox is not the reading we meant to send. That is how the same
        reading reached the ground several times.
        """
        self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        sessions_before = self.modem.commands.count("AT+SBDIX")

        self.modem.write_silently_fails = True
        ok, _ = self.radio.send_tracking_data_with_retry(*READING_B, max_attempts=2)

        self.assertFalse(ok)
        self.assertEqual(
            self.modem.commands.count("AT+SBDIX"), sessions_before,
            "started a session without confirming the write landed",
        )

    def test_a_rejected_write_does_not_start_a_session(self):
        self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)

        self.modem.fail_next_write = True
        ok, _ = self.radio.send_tracking_data_with_retry(*READING_B, max_attempts=2)

        self.assertFalse(ok)
        self.assertEqual(len(self.modem.sent), 1, "the old reading was sent again")

    def test_the_outbox_is_emptied_before_each_new_write(self):
        self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        clear_index = self.modem.commands.index("AT+SBDD0")
        write_index = next(i for i, c in enumerate(self.modem.commands)
                           if c.startswith("AT+SBDWT="))
        self.assertLess(clear_index, write_index)

    def test_nothing_is_sent_when_the_outbox_is_empty(self):
        self.modem.fail_next_write = True
        ok, _ = self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        self.assertFalse(ok)
        self.assertEqual(self.modem.sent, [])
        self.assertNotIn("AT+SBDIX", self.modem.commands)

    def test_the_momsn_is_recorded(self):
        self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        self.assertEqual(self.radio.last_session['momsn'], 101)

    def test_flow_control_is_turned_off_at_boot(self):
        self.assertIn("AT&K0", self.modem.commands)
        self.assertTrue(self.radio.flow_control_off)

    def test_signal_is_not_checked_before_sending(self):
        # AT+CSQ costs ~20s and Ground Control advise against it.
        self.radio.send_tracking_data_with_retry(*READING_A, max_attempts=2)
        self.assertNotIn("AT+CSQ", self.modem.commands)


if __name__ == "__main__":
    unittest.main()
