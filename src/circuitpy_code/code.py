import board
import digitalio
import microcontroller
import neopixel
import time
import busio
import analogio
from gps_module import GPSModule
from simple_oled import SimpleOLED  
from altitude_module import AltitudeSensor, celsius_to_fahrenheit
from rockblock_module import SimpleRockBLOCK

# ===========================================
# CONFIGURATION
# ===========================================
SATELLITE_ENABLED = True
SATELLITE_INTERVAL_SECONDS = 300  # 5 minutes
REQUIRE_GPS_FOR_SATELLITE = True
MIN_SIGNAL_STRENGTH = 0  # 0 = disabled, 1-5 = minimum required
RETRY_FAILED_AFTER_SECONDS = 30
# ===========================================

class HABTracker:
    def __init__(self):
        # Status tracking
        self.satellite_success_count = 0
        self.satellite_fail_count = 0
        self.next_satellite_time = 0  # Send immediately on startup
        
        # Initialize hardware
        self.led = digitalio.DigitalInOut(board.LED)
        self.led.direction = digitalio.Direction.OUTPUT
        self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)
        
        # Initialize all components
        self._initialize_hardware()
    
    def _show_boot_status(self, message, line2=""):
        """Display boot status on OLED and serial"""
        print(message)
        if line2:
            print(line2)
        
        if hasattr(self, 'oled') and self.oled:
            try:
                self.oled.clear()
                self.oled.add_text("HAB Tracker")
                self.oled.add_text(message)
                if line2:
                    self.oled.add_text(line2)
            except:
                pass
        time.sleep(2)
    
    def _initialize_hardware(self):
        """Initialize all hardware components"""
        # OLED Display
        try:
            self.oled = SimpleOLED()
            self.oled.add_text("HAB Tracker")
            self.oled.add_text("Booting...")
        except:
            self.oled = None
        
        self._show_boot_status("Init sensors...")
        self.i2c = board.I2C()
        
        # Battery monitoring
        try:
            self.battery_voltage = analogio.AnalogIn(board.A0)
            self._show_boot_status("Battery: OK")
        except:
            self.battery_voltage = None
            self._show_boot_status("Battery: FAIL")
        
        # Altitude/Temperature sensor
        try:
            self.bmp_sensor = AltitudeSensor(self.i2c)
            self._show_boot_status("BMP280: OK")
        except:
            self.bmp_sensor = None
            self._show_boot_status("BMP280: FAIL")
        
        # GPS
        try:
            self.gps = GPSModule(self.i2c)
            self._show_boot_status("GPS: OK")
        except:
            self.gps = None
            self._show_boot_status("GPS: FAIL")
        
        # Satellite Modem (RockBLOCK) - Required!
        try:
            time.sleep(3)
            self.rockblock = SimpleRockBLOCK(debug=True)
            
            if not self.rockblock.model:
                self._show_boot_status("RockBLOCK: FAIL", "Check power!")
                while True:
                    time.sleep(10)
            
            imei_short = self.rockblock.serial_number[-6:] if self.rockblock.serial_number else 'Unknown'
            self._show_boot_status("RockBLOCK: OK", f"IMEI: {imei_short}")
        except Exception as e:
            self._show_boot_status("RockBLOCK: FAIL", "Check wiring!")
            while True:
                time.sleep(10)
        
        self._show_boot_status("Ready!")
        time.sleep(1)
    
    def get_battery_voltage(self):
        """Read battery voltage"""
        if not self.battery_voltage:
            return None
        try:
            return (self.battery_voltage.value / 65535.0) * 3.3
        except:
            return None
    
    def collect_data(self):
        """Collect all sensor readings"""
        data = {
            'lat': None, 'lon': None, 'altitude': None,
            'satellites': 0, 'battery': None, 'temperature': None,
            'has_gps_fix': False
        }
        
        # GPS data
        if self.gps:
            self.gps.update()
            data['has_gps_fix'] = self.gps.has_fix
            data['satellites'] = self.gps.get_satellites()
            if self.gps.has_fix:
                location = self.gps.get_location()
                if location:
                    data['lat'], data['lon'] = location
        
        # Altitude and temperature
        if self.bmp_sensor:
            data['altitude'] = self.bmp_sensor.get_altitude()
            data['temperature'] = self.bmp_sensor.get_temperature()
        
        # Battery
        data['battery'] = self.get_battery_voltage()
        
        return data
    
    def try_send_satellite(self, data):
        """Try to send satellite message"""
        if not SATELLITE_ENABLED:
            return False
            
        # Check GPS requirement
        if REQUIRE_GPS_FOR_SATELLITE and not data['has_gps_fix']:
            print("📡 Waiting for GPS lock to send...")
            # Check again in 30 seconds
            self.next_satellite_time = time.time() + 30
            return False
        
        # Check signal strength
        signal = self.rockblock.check_signal()
        print(f"📡 Signal: {signal}/5")
        
        if signal < MIN_SIGNAL_STRENGTH:
            print(f"❌ Signal too weak - need {MIN_SIGNAL_STRENGTH}/5")
            return False
        
        # Show transmitting message
        if self.oled:
            self.oled.clear()
            self.oled.add_text("TRANSMITTING")
            self.oled.add_text(f"{data['lat']:.2f},{data['lon']:.2f}")
            self.oled.add_text(f"{data['altitude'] or 0}m")
        
        # Send the message
        print(f"📡 Sending: {data['lat']:.4f},{data['lon']:.4f} alt:{data['altitude']}m")
        success, _ = self.rockblock.send_tracking_data_with_retry(
            data['lat'], data['lon'], data['altitude'], 
            data['satellites'], data['battery'], data['temperature'], 
            max_attempts=2
        )
        
        return success
    
    def update_led(self, data):
        """Update status LED color"""
        if not data['has_gps_fix'] and self.gps:
            self.pixels.fill((0, 0, 255))    # Blue - GPS searching
        elif data['has_gps_fix']:
            self.pixels.fill((0, 255, 0))    # Green - GPS locked
        else:
            self.pixels.fill((255, 255, 0))  # Yellow - No GPS
    
    def update_display(self, screen, data):
        """Update OLED display"""
        if not self.oled:
            return
            
        try:
            self.oled.clear()
            
            if screen == 0:  # Temperature
                self.oled.add_text(f"{data['temperature'] or 'N/A'}°F")
                self.oled.add_text("Temperature")
                
            elif screen == 1:  # Altitude  
                self.oled.add_text(f"{data['altitude'] or 'N/A'}m")
                self.oled.add_text("Altitude")
                
            elif screen == 2:  # GPS
                if self.gps:
                    if data['has_gps_fix'] and data['lat'] and data['lon']:
                        self.oled.add_text(f"{data['lat']:.4f}")
                        self.oled.add_text(f"{data['lon']:.4f}")
                        self.oled.add_text(f"Satellites: {data['satellites']}")
                    else:
                        self.oled.add_text("GPS searching...")
                        self.oled.add_text(f"Satellites: {data['satellites']}")
                else:
                    self.oled.add_text("GPS OFFLINE")
                    
            elif screen == 3:  # Battery
                if data['battery']:
                    self.oled.add_text(f"{data['battery']:.2f}V")
                    self.oled.add_text("Battery")
                else:
                    self.oled.add_text("No battery")
                    
            elif screen == 4:  # Satellite Status
                if REQUIRE_GPS_FOR_SATELLITE and not data['has_gps_fix']:
                    self.oled.add_text("Waiting for GPS")
                    self.oled.add_text(f"Sats: {data['satellites']}")
                else:
                    self.oled.add_text(f"Sent: {self.satellite_success_count}")
                    self.oled.add_text(f"Failed: {self.satellite_fail_count}")
                    
        except:
            pass
    
    def run(self):
        """Main loop"""
        print("\n=== HAB TRACKER STARTED ===")
        print(f"Satellite: {'ON' if SATELLITE_ENABLED else 'OFF'}")
        
        counter = 0
        last_status_time = 0
        
        while True:
            # Collect sensor data
            data = self.collect_data()
            
            # Print status every 10 seconds
            if time.time() - last_status_time >= 10:
                print(f"\n--- Status ---")
                if self.bmp_sensor:
                    print(f"Temp: {data['temperature']}°F, Alt: {data['altitude']}m")
                if data['battery']:
                    print(f"Battery: {data['battery']:.2f}V")
                if self.gps:
                    if data['has_gps_fix']:
                        print(f"GPS: ({data['lat']}, {data['lon']}), Sats: {data['satellites']}")
                    else:
                        print(f"GPS: Searching... Sats: {data['satellites']}")
                last_status_time = time.time()
            
            # Check if time to send satellite message
            if SATELLITE_ENABLED and time.time() >= self.next_satellite_time:
                print(f"\n📡 Satellite transmission...")
                
                success = self.try_send_satellite(data)
                
                if success:
                    self.satellite_success_count += 1
                    self.next_satellite_time = time.time() + SATELLITE_INTERVAL_SECONDS
                    print(f"✅ SUCCESS! Total: {self.satellite_success_count}")
                    
                    if self.oled:
                        self.oled.clear()
                        self.oled.add_text("SENT OK!")
                        self.oled.add_text(f"Total: {self.satellite_success_count}")
                        time.sleep(3)
                elif data['has_gps_fix'] or not REQUIRE_GPS_FOR_SATELLITE:
                    # Only count as failure if we actually tried to send
                    self.satellite_fail_count += 1
                    self.next_satellite_time = time.time() + RETRY_FAILED_AFTER_SECONDS
                    print(f"❌ FAILED! Retry in {RETRY_FAILED_AFTER_SECONDS}s")
                    
                    if self.oled:
                        self.oled.clear()
                        self.oled.add_text("SEND FAILED")
                        self.oled.add_text(f"Retry in {RETRY_FAILED_AFTER_SECONDS}s")
                        time.sleep(3)
            
            # Update displays
            self.update_led(data)
            self.update_display(counter % 5, data)
            
            # Heartbeat LED
            self.led.value = True
            time.sleep(1)
            self.led.value = False
            time.sleep(1)
            
            counter += 1


# Run the tracker
if __name__ == "__main__":
    tracker = HABTracker()
    tracker.run()