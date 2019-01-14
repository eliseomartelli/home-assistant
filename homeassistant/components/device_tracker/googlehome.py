"""
Support for Google Home bluetooth tacker.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.googlehome/
"""
import logging
from datetime import timedelta

from homeassistant.components.device_tracker import DeviceScanner
from homeassistant.components.googlehome import CLIENT, NAME
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify

DEPENDENCIES = ['googlehome']

DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    """Validate the configuration and return a Google Home scanner."""
    scanner = GoogleHomeDeviceScanner(hass, hass.data[CLIENT],
                                      discovery_info, async_see)
    return await scanner.async_init()


class GoogleHomeDeviceScanner(DeviceScanner):
    """This class queries a Google Home unit."""

    def __init__(self, hass, client, config, async_see):
        """Initialize the scanner."""
        self.async_see = async_see
        self.hass = hass
        self.rssi = config['rssi_threshold']
        self.device_types = config['device_types']
        self.host = config['host']
        self.client = client

    async def async_init(self):
        """Further initialize connection to Google Home."""
        await self.client.update_data(self.host)
        data = self.hass.data[NAME][self.host]
        info = data.get('info', {})
        connected = bool(info)
        if connected:
            await self.async_update()
            async_track_time_interval(self.hass,
                                      self.async_update,
                                      DEFAULT_SCAN_INTERVAL)
        return connected

    async def async_update(self, now=None):
        """Ensure the information from Google Home is up to date."""
        _LOGGER.debug('Checking Devices on %s', self.host)
        await self.client.update_data(self.host)
        data = self.hass.data[NAME][self.host]
        info = data.get('info')
        bluetooth = data.get('bluetooth')
        if info is None or bluetooth is None:
            return
        google_home_name = info.get('name', NAME)

        for device in bluetooth:
            if device['device_type'] not in self.device_types:
                continue

            elif  device['rssi'] < self.rssi:
                continue

            name = "{} {}".format(self.host, device['mac_address'])

            attributes = {}
            attributes['btle_mac_address'] = device['mac_address']
            attributes['ghname'] = google_home_name
            attributes['rssi'] = device['rssi']
            attributes['source_type'] = 'bluetooth'
            if device['name']:
                attributes['name'] = device['name']

            await self.async_see(dev_id=slugify(name),
                                 attributes=attributes)
