import board
import busio
import time
from adafruit_rockblock import RockBlock

class SimpleRockBLOCK:
    def __init__(self, debug=False):
        """Initialize the RockBLOCK module with basic info."""
        self.debug = debug
        self.available = False
        self.model = None
        self.serial_number = None
        self.rockblock = None
        
        if self.debug:
            print("Initializing RockBLOCK...")
        
        try:
            # Create UART connection
            self.uart = busio.UART(board.D1, board.D0, baudrate=19200, timeout=1)
            if self.debug:
                print("✓ UART created")
            
            # Create RockBLOCK object
            self.rockblock = RockBlock(self.uart)
            if self.debug:
                print("✓ RockBLOCK object created")
            
            # Allow modem to settle
            time.sleep(1)
            
            # Get basic info
            self._get_modem_info()
            
            if self.model or self.serial_number:
                self.available = True
                if self.debug:
                    print("✓ RockBLOCK initialized successfully")
            else:
                if self.debug:
                    print("⚠️  RockBLOCK responding but no info retrieved")
                    
        except Exception as e:
            if self.debug:
                print(f"✗ RockBLOCK initialization failed: {e}")
            self.available = False
    
    def _get_modem_info(self):
        """Get basic modem information."""
        try:
            # Get model
            self.model = self.rockblock.model
            if self.debug and self.model:
                print(f"Model: {self.model}")
            
            time.sleep(1)  # Allow modem to settle
            
            # Get serial number/IMEI
            self.serial_number = self.rockblock.serial_number
            if self.debug and self.serial_number:
                print(f"Serial: {self.serial_number}")
                
        except Exception as e:
            if self.debug:
                print(f"Error getting modem info: {e}")
    
    def get_model_short(self):
        """Get first few characters of model for display."""
        if not self.model:
            return "No Model"
        # Return first 8 characters to fit on OLED
        return self.model[:8]
    
    def get_serial_short(self):
        """Get last 6 digits of serial for display."""
        if not self.serial_number:
            return "No Serial"
        # Return last 6 characters (like IMEI display)
        return f"...{self.serial_number[-6:]}"
    
    def get_status(self):
        """Get simple status string for display."""
        if self.available:
            return "RockBLOCK OK"
        else:
            return "RockBLOCK ERR"
    
    def print_info(self):
        """Print full modem information."""
        if not self.available:
            print("RockBLOCK not available")
            return
        
        print("RockBLOCK Information:")
        print(f"  Model: {self.model or 'Unknown'}")
        print(f"  Serial: {self.serial_number or 'Unknown'}")
        print(f"  Status: Available")
    
    def refresh_info(self):
        """Refresh modem information (call occasionally)."""
        if self.available:
            try:
                self._get_modem_info()
            except Exception as e:
                if self.debug:
                    print(f"Error refreshing info: {e}")