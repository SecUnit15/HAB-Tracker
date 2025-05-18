import board
import digitalio
import microcontroller
import neopixel
import time
import busio
import adafruit_bmp280
from gps_module import GPSModule
from simple_oled import SimpleOLED  # Import our simple OLED helper

# Initialize digital I/O
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Initialize NeoPixel
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)

print("Starting initialization...")

# Create I2C bus
print("Initializing I2C bus...")
i2c = board.I2C()  # Use the board's I2C bus

# Wait for I2C to be ready
time.sleep(0.5)

# Initialize the BMP sensor
print("Initializing BMP280 sensor...")
try:
    bmp_sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
    bmp_sensor.sea_level_pressure = 1014.9
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

# Initialize OLED display - super easy now!
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

def celsius_to_fahrenheit(temp_c):
    temp_f = temp_c * (9/5) + 32
    return int(temp_f)

def print_bmp_sensor():
    if not bmp_available:
        print("BMP280 sensor not available")
        return
    
    try:
        outside_temp_f = celsius_to_fahrenheit(bmp_sensor.temperature)
        print(f'Outside temp is: {outside_temp_f} degrees F')
        print(f'Outside pressure is: {int(bmp_sensor.pressure)}hPa')
        print(f'Altitude: {int(bmp_sensor.altitude)} meters')
        return outside_temp_f
    except Exception as e:
        print(f"Error reading BMP280: {e}")
        return None

def print_cpu_temp():
    try:
        cpu_temp_fahrenheit = celsius_to_fahrenheit(microcontroller.cpu.temperature)
        print(f"The CPU temperature is {cpu_temp_fahrenheit} degrees F")
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")

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
            
            # Print altitude if available (this is separate from BMP280 altitude)
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


def update_status_led():
    """Update the NeoPixel color to show system status.
    
    GREEN = Everything good + GPS lock
    BLUE = Waiting for GPS fix
    RED = System problem
    """
    # Simple color codes 
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    RED = (255, 0, 0)
    
    # Check GPS status
    if gps_available and gps.has_fix:
        # We have GPS lock - show green!
        pixels.fill(GREEN)
    elif gps_available and not gps.has_fix:
        # GPS is working but waiting for fix - show blue
        pixels.fill(BLUE)
    else:
        # Something's wrong - show red
        pixels.fill(RED)

def update_display(counter):
    """Update the OLED display with sensor data.
    
    This function shows one screen of data on the OLED display.
    You can modify this function to show different screens!
    """
    if not oled_available:
        return
    
    try:
        # Clear the display to start fresh
        oled.clear()
        
        # Show a title for this screen
        oled.add_text("Temperature")
        
        # Show the temperature if available
        if bmp_available:
            temp_f = celsius_to_fahrenheit(bmp_sensor.temperature)
            oled.add_text(f"{temp_f} F")
        else:
            oled.add_text("Sensor offline")
            
        # Show the counter as well
        oled.add_text(f"Count: {counter}")
        
        # === ADD MORE SCREENS HERE ===
        # To add more screens, you can use the counter to decide 
        # which screen to show. For example:
        #
        # if counter % 3 == 0:
        #     # Show screen 1 (temperature)
        #     oled.clear()
        #     oled.add_text("Temperature")
        #     ...
        # elif counter % 3 == 1:
        #     # Show screen 2 (pressure)
        #     oled.clear()
        #     oled.add_text("Pressure")
        #     ...
        # elif counter % 3 == 2:
        #     # Show screen 3 (GPS)
        #     oled.clear()
        #     oled.add_text("GPS Data") 
        #     ...
        
    except Exception as e:
        print(f"Error updating display: {e}")

print("Starting main loop...")

# Counter for display
display_counter = 0

while True:
    print("\n" + "=" * 40)  # Separator line
    print("SENSOR READINGS:")
    print_cpu_temp()
    print_bmp_sensor()
    print("\nGPS DATA:")
    print_gps_data()
    
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