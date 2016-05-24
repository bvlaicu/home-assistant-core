"""
LIRC interface to receive signals from a infrared remote control.

This sensor will momentarily set state to various values as defined
in the .lintrc file which can be interpreted in home-assistant to
trigger various actions.

Sending signals to other IR receivers can be accomplished with the
shell_command component and the irsend command for now.
"""
# pylint: disable=import-error
import threading
import time
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STOP

REQUIREMENTS = ['python-lirc>=1.2.1']
_LOGGER = logging.getLogger(__name__)
ICON = 'mdi:remote'
EVENT_BUTTON_PRESSED = 'button_pressed'
BUTTON_NAME = 'button_name'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup LIRC capability."""
    # Perform safe import of third-party python-lirc module
    try:
        import lirc
    except ImportError:
        _LOGGER.error("You are missing a required dependency: python-lirc.")
        return False

    # blocking=True gives unexpected behavior (multiple responses for 1 press)
    # also by not blocking, we allow hass to shut down the thread gracefully
    # on exit.
    lirc.init('home-assistant', blocking=False)
    lirc_interface = LircInterface(hass)
    lirc_interface.start()

    def _stop_lirc(_event):
        lirc_interface.stopped.set()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, _stop_lirc)

    return True


class LircInterface(threading.Thread):
    """
    This interfaces with the lirc daemon to read IR commands.

    When using lirc in blocking mode, sometimes repeated commands get produced
    in the next read of a command so we use a thread here to just wait
    around until a non-empty response is obtained from lirc.
    """

    def __init__(self, hass):
        """Construct a LIRC interface object."""
        threading.Thread.__init__(self)
        self.stopped = threading.Event()
        self.hass = hass

    def run(self):
        """Main loop of LIRC interface thread."""
        import lirc
        while not self.stopped.isSet():
            code = lirc.nextcode()  # list; empty if no buttons pressed
            # interpret result from python-lirc
            if code:
                code = code[0]
                _LOGGER.info('Got new LIRC code %s', code)
                self.hass.bus.fire(EVENT_BUTTON_PRESSED, {BUTTON_NAME: code})
            else:
                time.sleep(0.1)  # avoid high CPU in this thread

        _LOGGER.info('LIRC interface thread stopped')
