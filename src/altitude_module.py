import adafruit_bmp280

def celsius_to_fahrenheit(temp_c):
    temp_f = temp_c * (9/5) + 32
    return int(temp_f)

class AltitudeSensor:
    def __init__(self, i2c):
        # set up altitude sensor
        self.bmp_sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
        self.bmp_sensor.sea_level_pressure = 1013.9 # sd sea level pressure

    def get_altitude(self):
        #return altitude in meters
        return int(self.bmp_sensor.altitude)

    def get_temperature(self):
        #return temperature in fahrenheit
        return celsius_to_fahrenheit(self.bmp_sensor.temperature)
    
    def get_pressure(self):
        #return pressure hPa
        return int(self.bmp_sensor.pressure)