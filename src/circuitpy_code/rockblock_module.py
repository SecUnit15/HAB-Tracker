import time
import busio
import board
import telemetry

class SimpleRockBLOCK:
    """Simplified RockBLOCK satellite modem interface for HAB tracking"""
    
    def __init__(self, debug=False, uart=None):
        self.debug = debug
        # uart can be supplied so tests can drive the modem without hardware.
        self.uart = uart or busio.UART(board.D1, board.D0, baudrate=19200, timeout=1)
        self.model = None
        self.serial_number = None
        # Details of the most recent satellite session, including its MOMSN.
        self.last_session = None
        self.flow_control_off = False

        # Initialize modem
        self._initialize()
    
    def _initialize(self):
        """Initialize modem and get basic info"""
        try:
            time.sleep(2)  # Let modem settle
            
            # Check if modem is responding
            response = self._send_at_command("")
            if "OK" in str(response):
                if self.debug:
                    print("✅ Modem responding")

            # We wire the modem with only TX/RX/GND, so there are no flow
            # control lines for it to use. AT&K0 turns that off. Without it we
            # inherit whatever the modem was last set to, which makes dropped
            # and garbled bytes hard to reproduce on the bench.
            self.flow_control_off = "OK" in str(self._send_at_command("&K0"))
            if self.debug and not self.flow_control_off:
                print("⚠️ AT&K0 was not confirmed")

            # Get IMEI (serial number)
            self._get_imei()
            
            self.model = "RockBLOCK" if self.serial_number else None
            
            if self.debug:
                print(f"Model: {self.model}")
                print(f"IMEI: {self.serial_number}")
                
        except Exception as e:
            if self.debug:
                print(f"Init error: {e}")
    
    def _get_imei(self):
        """Get modem IMEI (serial number)"""
        imei_resp = self._send_at_command("+CGSN")
        for line in imei_resp:
            # IMEI is a long number (15+ digits)
            if line.isdigit() and len(line) > 10:
                self.serial_number = line
                break
    
    def _send_at_command(self, command, timeout=10):
        """Send AT command and return response lines"""
        try:
            # Clear any old data
            self.uart.reset_input_buffer()
            
            # Send command
            full_command = f"AT{command}\r"
            self.uart.write(full_command.encode())
            
            # Read response
            response = []
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                line = self.uart.readline()
                if line:
                    decoded = line.decode().strip()
                    if decoded:  # Only add non-empty lines
                        response.append(decoded)
                        # Stop when we see OK or ERROR
                        if "OK" in decoded or "ERROR" in decoded:
                            break
            
            return response
            
        except Exception as e:
            return [f"ERROR: {e}"]
    
    def check_signal(self):
        """Get Iridium signal strength (0-5 bars). Bench diagnostics only.

        Do not call this before a send: it costs about 20 seconds, and the sky
        can change in that time. Start the session instead and let it fail.
        """
        try:
            response = self._send_at_command("+CSQ", timeout=5)
            
            if self.debug:
                print(f"Signal check response: {response}")
            
            # Look for signal strength line
            for line in response:
                if "+CSQ:" in line:
                    try:
                        # Extract number after the colon
                        signal_str = line.split(":")[1].strip()
                        signal = int(signal_str)
                        return signal
                    except (ValueError, IndexError):
                        continue
            
            # No signal found
            if self.debug:
                print("No signal response found")
            return 0
            
        except Exception as e:
            if self.debug:
                print(f"Signal check error: {e}")
            return 0
    
    def send_tracking_data_with_retry(self, boot_id, sequence, lat, lon, altitude,
                                      satellites, battery, temperature,
                                      fix_age_s, max_attempts=3):
        """Send tracking data with automatic retry"""

        message = telemetry.build_message(
            boot_id, sequence, lat, lon, altitude, satellites,
            battery, temperature, fix_age_s
        )
        
        if self.debug:
            print(f"📡 Sending: {message}")
        
        # First, set the message to send
        if not self._set_message(message):
            return False, None
        
        # Try to send with retries
        for attempt in range(max_attempts):
            if self.debug:
                print(f"📡 Send attempt {attempt + 1}/{max_attempts}")
            
            status_code = self._send_message()
            
            if status_code is not None:
                # Iridium says 0-4 = delivered, 5-8 = session FAILED.
                # We used to accept <= 8, so a failed send looked like a success
                # and we skipped the retry - silently losing that reading.
                if telemetry.is_delivered(status_code):
                    # Empty the outbox now it is delivered, so a stray later
                    # session has nothing to send a second time.
                    self._send_at_command("+SBDD0")
                    if self.debug:
                        print("✅ Message sent successfully!")
                    return True, status_code
                
                # Handle specific errors
                elif status_code == 32:
                    # Network unavailable - retry after delay
                    if self.debug:
                        print("⚠️ Network unavailable - will retry")
                    if attempt < max_attempts - 1:
                        time.sleep(30)
                    
                elif status_code == 15:
                    # 15 = access denied. Retrying cannot fix this one.
                    # 13 (session did not complete) and 14 (bad segment size)
                    # used to land here too, but those are temporary - they now
                    # fall through to the normal retry below.
                    if self.debug:
                        print(f"❌ Access denied ({status_code})")
                    return False, status_code
                    
                else:
                    # Other error - retry after short delay
                    if self.debug:
                        print(f"⚠️ Error {status_code} - will retry")
                    if attempt < max_attempts - 1:
                        time.sleep(15)
            else:
                # No response - retry after short delay
                if self.debug:
                    print("❌ No response received")
                if attempt < max_attempts - 1:
                    time.sleep(10)
        
        # All attempts failed
        if self.debug:
            print(f"❌ All {max_attempts} attempts failed")
        return False, None
    
    def _set_message(self, message):
        """Load one message into the modem's outbox, ready to send.

        The rule this enforces: never start a session unless this returned
        True. The modem has no command to read the outbox back, so we empty it
        first and then confirm something is in it. A failed write therefore
        leaves the outbox empty instead of leaving the previous message there.
        """
        try:
            # Empty the outbox first. If the write below fails, there is then
            # nothing stale left for a session to pick up and send again.
            if "OK" not in str(self._send_at_command("+SBDD0")):
                if self.debug:
                    print("❌ Could not clear the outbox")
                return False

            # AT+SBDWT wants bare text. The quotes we used to wrap around it
            # were stored as part of the message and had to be stripped later.
            if "OK" not in str(self._send_at_command(f"+SBDWT={message}")):
                if self.debug:
                    print("❌ Failed to set message")
                return False

            # +SBDS cannot show us the text, but it does say whether a message
            # is now waiting - which is enough to know the write landed.
            if not self._outbox_has_message():
                if self.debug:
                    print("❌ Outbox still empty after write - not sending")
                return False

            return True

        except Exception as e:
            if self.debug:
                print(f"❌ Set message error: {e}")
            return False

    def _outbox_has_message(self):
        """True if +SBDS reports a message waiting in the outbox."""
        for line in self._send_at_command("+SBDS"):
            waiting = telemetry.outbox_has_message(line)
            if waiting is not None:
                return waiting
        return False
    
    def _send_message(self):
        """Send message via satellite"""
        try:
            # Send command (long timeout for satellite connection)
            response = self._send_at_command("+SBDIX", timeout=180)
            
            # Parse response
            for line in response:
                session = telemetry.parse_sbdix(line)
                if session is None:
                    continue

                # The MOMSN in here is the ID Iridium gave this message, which
                # is how the ground can tell a resend from a new reading.
                self.last_session = session

                if self.debug:
                    print(f"Status code: {session['mo_status']}"
                          f"  MOMSN: {session['momsn']}")

                return session['mo_status']
            
            # No valid response found
            return None
            
        except Exception as e:
            if self.debug:
                print(f"❌ Send error: {e}")
            return None