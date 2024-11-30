# utils/logger.py

import logging

# Configure the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set the desired logging level (DEBUG, INFO, ERROR, etc.)

# Create console handler for logging to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Adjust the level if needed

# Create a formatter for the log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)


