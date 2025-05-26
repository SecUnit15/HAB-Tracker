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
from rockblock_module import SimpleRockBLOCK  # Your new module

# Wait for I2C to be ready
time.sleep(1.0)

# Initialize digital I/O
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Initialize NeoPixel
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)

# Initialize battery voltage monitoring
print("Initializing battery voltage monitor...")
try:
    battery_voltage = analogio.AnalogIn(board.A0)
    print("Battery voltage monitor initialized on A0")
    battery_available = True
except Exception as e:
    print(f"Error initializing battery monitor: {e}")
    battery_available = False

print("Starting initialization...")

# Create I2C bus
print("Initializing I2C bus...")
i2c = board.I2C()  # Use the board's I2C bus

# Initialize the BMP sensor
print("Initializing BMP280 sensor...")
try:
    bmp_sensor = AltitudeSensor(i2c)
    print("BMP280 sensor initialized successfully")
    bmp_available = True
except Exception as e:
    print(f"Error initializing BMP280: {e}")
    bmp_available = False

# Initialize the GPS module
print("Initializing GPS module...")
try:
    gps = GPSModule(i2c)
    print("GPS module initialized successfully")
    gps_available = True
except Exception as e:
    print(f"Error initializing GPS: {e}")
    gps_available = False

# Initialize OLED display
print("Initializing OLED display...")
try:
    oled = SimpleOLED()
    print("OLED display initialized successfully")
    oled_available = True
    
    # Show welcome message
    oled.add_text("Sensors ready!")
    oled.add_text("Starting...")
except Exception as e:
    print(f"Error initializing OLED: {e}")
    oled_available = False

# Initialize RockBLOCK module
print("Initializing RockBLOCK module..")
try:
    print("Sleeping 5.0 sec to let modem initialize.")
    time.sleep(5.0)
    rockblock = SimpleRockBLOCK(debug=True)
    print("Sleeping 5.0 sec to let modem initialize.")
    time.sleep(5.0)
    print("RockBLOCK module initialized")
    print(f"Model: {rockblock.model}")
    print(f"IMEI: {rockblock.serial_number}")
    rockblock_available = rockblock.available
except Exception as e:
    print(f"Error initializing RockBLOCK: {e}")
    rockblock_available = False
    rockblock = None

def get_battery_voltage():
    """Simple battery voltage reading."""
    if not battery_available:
        return None
    
    try:
        # Read analog value and convert to voltage
        voltage = (battery_voltage.value / 65535.0) * 3.3 
        return voltage
    except:
        return None

def print_bmp_sensor():
    if not bmp_available:
        print("BMP280 sensor not available")
        return
    
    try:
        print(f'Outside temp is: {bmp_sensor.get_temperature()} degrees F')
        print(f'Outside pressure is: {bmp_sensor.get_pressure()} hPa')
        print(f'Altitude: {bmp_sensor.get_altitude()} meters')
    except Exception as e:
        print(f"Error reading BMP280: {e}")

def print_cpu_temp():
    try:
        cpu_temp_fahrenheit = celsius_to_fahrenheit(microcontroller.cpu.temperature)
        print(f"The CPU temperature is {cpu_temp_fahrenheit} degrees F")
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")

def print_battery_info():
    """Print battery voltage."""
    voltage = get_battery_voltage()
    if voltage:
        print(f"Battery voltage: {voltage:.2f}V")
    else:
        print("Battery: not available")

def print_gps_data():
    if not gps_available:
        print("GPS module not available")
        return
    
    try:
        # Update GPS data
        gps.update()
        
        # Check if we have a fix
        if gps.has_fix:
            # Print basic GPS data
            location = gps.get_location()
            if location:
                lat, lon = location
                print(f"GPS Position: {lat:.6f}, {lon:.6f}") 
            
            # Print altitude if available
            gps_altitude = gps.get_altitude()
            if gps_altitude is not None:
                print(f"GPS Altitude: {int(gps_altitude)} meters")
            
            # Print speed if available
            speed = gps.get_speed('kmh')
            if speed is not None:
                print(f"Speed: {int(speed)} km/h")
            
            # Print satellites if available
            satellites = gps.get_satellites()
            if satellites is not None:
                print(f"Satellites: {satellites}")
        else:
            print("GPS: Waiting for fix...")
    except Exception as e:
        print(f"Error reading GPS data: {e}")

def print_rockblock_info():
    """Print just the current RockBLOCK status."""
    if not rockblock_available:
        print("RockBLOCK: offline")
        return
    
    try:
        signal = rockblock.signal_quality or 0
        connected = "Yes" if rockblock.system_time else "No"
        print(f"RockBLOCK: {signal}/5 bars, Connected: {connected}")
    except Exception as e:
        print(f"RockBLOCK: error")

def update_status_led():
    """Update the NeoPixel color to show system status.
    
    GREEN = Everything good + GPS lock
    BLUE = Waiting for GPS fix  
    YELLOW = RockBLOCK issues
    RED = System problem
    """
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    RED = (255, 0, 0)
    
    # Check RockBLOCK status first
    if not rockblock_available:
        pixels.fill(YELLOW)
        return
    
    # Check GPS status
    if gps_available and gps.has_fix:
        pixels.fill(GREEN)
    elif gps_available and not gps.has_fix:
        pixels.fill(BLUE)
    else:
        pixels.fill(RED)

def update_display(counter):
    """Update the OLED display with sensor data."""
    if not oled_available:
        return
    
    try:
        # 5 screens now: temp, altitude, GPS, battery, RockBLOCK
        if counter % 5 == 0:
            # Temperature screen
            oled.clear()
            if bmp_available:
                temp_f = bmp_sensor.get_temperature()
                oled.add_text(f"{temp_f} F")
            else:
                oled.add_text("offline")
            oled.add_text("Temperature")
            
        elif counter % 5 == 1:
            # Altitude screen
            oled.clear()
            if bmp_available:
                oled.add_text(f"{bmp_sensor.get_altitude()} meters")
            else:
                oled.add_text("offline")
            oled.add_text("Altitude")
            
        elif counter % 5 == 2:
            # GPS screen
            oled.clear()
            if gps_available and gps.has_fix:
                location = gps.get_location()
                if location:
                    lat, lon = location
                    oled.add_text(f"{lat:.4f},{lon:.4f}")
                oled.add_text(f"Sats: {gps.get_satellites()}")
            else:
                oled.add_text("GPS offline")
                
        elif counter % 5 == 3:
            # Battery screen
            oled.clear()
            voltage = get_battery_voltage()
            if voltage:
                oled.add_text(f"{voltage:.2f} V")
            else:
                oled.add_text("No battery")
            oled.add_text("Battery")
                
        elif counter % 5 == 4:
            # RockBLOCK screen - NOW SHOWS STATUS
            oled.clear()
            if rockblock_available:
                try:
                    signal = rockblock.signal_quality or 0
                    connected = "Yes" if rockblock.system_time else "No"
                    oled.add_text(f"Signal: {signal}/5")
                    oled.add_text(f"Connected: {connected}")
                except:
                    oled.add_text("RockBLOCK")
                    oled.add_text("ERROR")
            else:
                oled.add_text("RockBLOCK")
                oled.add_text("OFFLINE")
        
    except Exception as e:
        print(f"Error updating display: {e}")

print("Starting main loop...")

# Counter for display
display_counter = 1

while True:
    if display_counter % 5 == 0:
        print("\n" + "=" * 40)
        print("SENSOR READINGS:")
        print_cpu_temp()
        print_bmp_sensor()
        print_battery_info()
        print("\nGPS DATA:")
        print_gps_data()
        print("\nROCKBLOCK STATUS:")
        print_rockblock_info()
    
    # Update the neopixel to show our sensor health at a glance 
    update_status_led()
    
    # Update the OLED display
    update_display(display_counter)
    display_counter += 1
    
    # Blink the main LED to show the program is running
    led.value = True
    time.sleep(1)
    led.value = False
    time.sleep(1)