# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import adafruit_gps

class GPSModule:
    def __init__(self, i2c_bus, debug=False, update_rate_ms=1000):
        """Initialize the GPS module.
        
        Args:
            i2c_bus: Existing I2C bus to use
            debug: Enable debug output from the GPS module
            update_rate_ms: Update rate in milliseconds (1000 = 1Hz)
        """
        # Initialize GPS with the provided I2C bus
        self.gps = adafruit_gps.GPS_GtopI2C(i2c_bus, debug=debug)
        
        # Initialize the GPS module - Enable GGA and RMC info
        self.gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
        
        # Set update rate (default: once a second)
        self.gps.send_command(f"PMTK220,{update_rate_ms}".encode())
        
        # Initialize variables
        self.last_update = time.monotonic()
        
    def update(self):
        """Update GPS data. Returns True if new data was parsed."""
        return self.gps.update()
    
    def check_fix(self, update_interval=1.0):
        """Check if GPS has a fix and update.
        
        Args:
            update_interval: How often to check for a fix (in seconds)
            
        Returns:
            True if there's a valid fix, False otherwise
        """
        current = time.monotonic()
        
        # Only check at specified interval
        if current - self.last_update >= update_interval:
            self.last_update = current
            
            # Make sure to update GPS data
            self.update()
            
            if not self.gps.has_fix:
                print("Waiting for fix...")
                return False
                
            return True
            
        return self.gps.has_fix
    
    def print_data(self):
        """Print all available GPS data."""
        if not self.gps.has_fix:
            print("No fix available")
            return
            
        print("=" * 40)  # Print a separator line
        
        # Print timestamp if available
        if self.gps.timestamp_utc:
            print(
                "Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}".format(
                    self.gps.timestamp_utc.tm_mon,
                    self.gps.timestamp_utc.tm_mday,
                    self.gps.timestamp_utc.tm_year,
                    self.gps.timestamp_utc.tm_hour,
                    self.gps.timestamp_utc.tm_min,
                    self.gps.timestamp_utc.tm_sec,
                )
            )
            
        # Location data
        print("Latitude: {0:.6f} degrees".format(self.gps.latitude))
        print("Longitude: {0:.6f} degrees".format(self.gps.longitude))
        print(
            "Precise Latitude: {} degs, {:2.4f} mins".format(
                self.gps.latitude_degrees, self.gps.latitude_minutes
            )
        )
        print(
            "Precise Longitude: {} degs, {:2.4f} mins".format(
                self.gps.longitude_degrees, self.gps.longitude_minutes
            )
        )
        
        print("Fix quality: {}".format(self.gps.fix_quality))
        
        # Print optional attributes if they exist
        if self.gps.satellites is not None:
            print("# satellites: {}".format(self.gps.satellites))
        if self.gps.altitude_m is not None:
            print("Altitude: {} meters".format(self.gps.altitude_m))
        if self.gps.speed_knots is not None:
            print("Speed: {} knots".format(self.gps.speed_knots))
        if self.gps.speed_kmh is not None:
            print("Speed: {} km/h".format(self.gps.speed_kmh))
        if self.gps.track_angle_deg is not None:
            print("Track angle: {} degrees".format(self.gps.track_angle_deg))
        if self.gps.horizontal_dilution is not None:
            print("Horizontal dilution: {}".format(self.gps.horizontal_dilution))
        if self.gps.height_geoid is not None:
            print("Height geoid: {} meters".format(self.gps.height_geoid))
    
    def get_location(self):
        """Get the current location as (latitude, longitude) tuple."""
        if not self.gps.has_fix:
            return None
        return (self.gps.latitude, self.gps.longitude)
    
    def get_altitude(self):
        """Get the current altitude in meters."""
        if not self.gps.has_fix or self.gps.altitude_m is None:
            return None
        return self.gps.altitude_m
    
    def get_speed(self, unit='kmh'):
        """Get the current speed in requested units.
        
        Args:
            unit: 'kmh' for kilometers per hour or 'knots'
            
        Returns:
            Speed in requested units or None if not available
        """
        if not self.gps.has_fix:
            return None
            
        if unit.lower() == 'kmh' and self.gps.speed_kmh is not None:
            return self.gps.speed_kmh
        elif unit.lower() == 'knots' and self.gps.speed_knots is not None:
            return self.gps.speed_knots
        return None
    
    def get_timestamp(self):
        """Get the current timestamp as a struct_time object."""
        if not self.gps.has_fix or self.gps.timestamp_utc is None:
            return None
        return self.gps.timestamp_utc
    
    def get_satellites(self):
        """Get the number of satellites being tracked."""
        if not self.gps.has_fix or self.gps.satellites is None:
            return None
        return self.gps.satellites
    
    @property
    def has_fix(self):
        """Check if the GPS has a fix."""
        return self.gps.has_fix