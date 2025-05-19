import board
import digitalio
import microcontroller
import neopixel
import time
import busio
from gps_module import GPSModule
from simple_oled import SimpleOLED  
from altitude_module import AltitudeSensor, celsius_to_fahrenheit

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
        # define sensor output screens
        if counter % 3 == 0:
            # Show screen 1 (temperature)
            oled.clear()
            if bmp_available:
                temp_f = bmp_sensor.get_temperature()
                oled.add_text(f"{temp_f} F")
            else:
                oled.add_text("offline")
            oled.add_text("Temperature")
        elif counter % 3 == 1:
            # Show screen 2 (pressure)
            oled.clear()
            if bmp_available:
                oled.add_text(f"{bmp_sensor.get_altitude()} meters")

            else:
                oled.add_text("offline")
            oled.add_text("Altitude")
        elif counter % 3 == 2:
            # Show screen 3 (GPS)
            oled.clear()
            if gps_available:
                oled.add_text(f"{gps.get_location()}")
                oled.add_text(f"Satellites: {gps.get_satellites()}")
            else:
                oled.add_text("offline")

            oled.add_text("GPS Data") 
        
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