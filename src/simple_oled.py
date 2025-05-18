# Simple OLED Display Helper for beginners
# Just import this and use it!

import board
import displayio
import terminalio
from adafruit_display_text import label
from i2cdisplaybus import I2CDisplayBus
import adafruit_displayio_ssd1306

class SimpleOLED:
    def __init__(self):
        """Initialize a simple OLED display - just create and use!"""
        # Release any existing displays
        displayio.release_displays()
        
        # Set up the display - these are the settings that work on your hardware
        i2c = board.I2C()
        reset_pin = board.D9
        display_bus = I2CDisplayBus(i2c, device_address=0x3D, reset=reset_pin)
        
        # 128x32 display (change to 64 if you have a taller display)
        self.width = 128
        self.height = 32
        
        # Create the display
        display = adafruit_displayio_ssd1306.SSD1306(
            display_bus, width=self.width, height=self.height
        )
        
        # Create a display group to hold everything
        self.group = displayio.Group()
        display.root_group = self.group
        
        # Start with a blank display
        self.clear()
        
        # Keep track of how many lines we've added
        self.line_count = 0
        
    def clear(self):
        """Clear everything from the display"""
        # Remove all items from the display group
        while len(self.group) > 0:
            self.group.pop()
        
        # Reset line counter
        self.line_count = 0
    
    def add_text(self, text, line=None):
        """Add a line of text to the display
        
        Args:
            text: The text to display
            line: Which line to put it on (0-3 for small display)
                 If None, adds to the next available line
        """
        # If line is not specified, use the next available line
        if line is None:
            line = self.line_count
            self.line_count += 1
        
        # Limit to what fits on the display
        max_lines = self.height // 10
        if line >= max_lines:
            print(f"Warning: Line {line} won't fit on display")
            return
        
        # Position text on the requested line (each line is about 10 pixels tall)
        y_position = 10 * line + 6
        
        # Create a text label
        text_label = label.Label(
            terminalio.FONT,
            text=text,
            color=0xFFFFFF,  # White
            x=0,
            y=y_position
        )
        
        # Add it to our display group
        self.group.append(text_label)
        
        # Return the index of this text in the group
        return len(self.group) - 1
    
    def update_text(self, text, index):
        """Update text at a specific position
        
        Args:
            text: New text to display
            index: Index returned from add_text
        """
        if 0 <= index < len(self.group):
            self.group[index].text = text