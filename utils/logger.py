# utils/logger.py
import os
import logging

# Configure the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the desired logging level (DEBUG, INFO, ERROR, etc.)

# Create console handler for logging to console
console_handler = logging.StreamHandler()
console_handler.setLevel(os.getenv('LOG_LEVEL', 'DEBUG').upper())  # Configurable via environment

# Create a formatter for the log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the console handler to the logger
if not logger.hasHandlers():
    logger.addHandler(console_handler)


