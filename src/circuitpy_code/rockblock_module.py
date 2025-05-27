import time
import busio
import board

class SimpleRockBLOCK:
    """Simplified RockBLOCK satellite modem interface for HAB tracking"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.uart = busio.UART(board.D1, board.D0, baudrate=19200, timeout=1)
        self.model = None
        self.serial_number = None
        
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
        """Get Iridium signal strength (0-5 bars)"""
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
    
    def send_tracking_data_with_retry(self, lat, lon, altitude, satellites, battery, temperature, max_attempts=3):
        """Send tracking data with automatic retry"""
        
        # Format message: lat|lon|altitude|satellites|battery|temperature
        message = f"{lat:.4f}|{lon:.4f}|{altitude or 0}|{satellites}|{battery or 0:.1f}|{temperature or 0:.0f}"
        
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
                # Success codes: 0-5 = sent, 6-8 = queued
                if status_code <= 8:
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
                    
                elif status_code in [13, 14, 15]:
                    # Account/credit error - stop trying
                    if self.debug:
                        print(f"❌ Account/credit error ({status_code})")
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
        """Set message in modem buffer"""
        try:
            command = f'+SBDWT="{message}"'
            response = self._send_at_command(command)
            
            if "OK" in str(response):
                return True
            else:
                if self.debug:
                    print("❌ Failed to set message")
                return False
                
        except Exception as e:
            if self.debug:
                print(f"❌ Set message error: {e}")
            return False
    
    def _send_message(self):
        """Send message via satellite"""
        try:
            # Send command (long timeout for satellite connection)
            response = self._send_at_command("+SBDIX", timeout=180)
            
            # Parse response
            for line in response:
                if "+SBDIX:" in line:
                    try:
                        # Extract status codes
                        status_part = line.split(":")[1].strip()
                        status_codes = status_part.split(",")
                        status_code = int(status_codes[0])
                        
                        if self.debug:
                            print(f"Status code: {status_code}")
                        
                        return status_code
                        
                    except (ValueError, IndexError) as e:
                        if self.debug:
                            print(f"Parse error: {e}")
                        continue
            
            # No valid response found
            return None
            
        except Exception as e:
            if self.debug:
                print(f"❌ Send error: {e}")
            return None