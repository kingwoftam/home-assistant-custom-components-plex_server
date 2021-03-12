"""
Monitors plex server for a particular machine_id. Reuses much of the code in the official
plex component for hass

For more details about the hass platform, please refer to the documentation at
https://home-assistant.io/components/sensor.plex/
"""
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_TVSHOW, MEDIA_TYPE_VIDEO)
from homeassistant.const import (
    DEVICE_DEFAULT_NAME, CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT, CONF_TOKEN)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_SERVER = 'server'

DEFAULT_HOST = 'localhost'
DEFAULT_NAME = 'PlexATV'
DEFAULT_PORT = 32400

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_TOKEN): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_SERVER): cv.string,
    vol.Optional(CONF_USERNAME): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Plex sensor."""
    name = config.get(CONF_NAME)
    plex_user = config.get(CONF_USERNAME)
    plex_password = config.get(CONF_PASSWORD)
    plex_server = config.get(CONF_SERVER)
    plex_host = config.get(CONF_HOST)
    plex_port = config.get(CONF_PORT)
    plex_token = config.get(CONF_TOKEN)
    plex_url = 'http://{}:{}'.format(plex_host, plex_port)
    
    add_devices([PlexServerSensor(
        name, plex_url, plex_user, plex_password, plex_server,
        plex_token)], True)

class PlexServerSensor(Entity):
    """Representation of a Plex now playing sensor."""
    
    def __init__(self, name, plex_url, plex_user, plex_password,
                 plex_server, plex_token):
        """Initialize the sensor."""
        from plexapi.myplex import MyPlexAccount
        from plexapi.server import PlexServer
        
        self._name = name
        self._state = 0
        self._media_attrs = {}
        self._sessions = None
        self._session = None
        self._sessioncount = 0
        self._session_type = None
        self._plex_url = plex_url
        self._plex_token = plex_token
        """Set all Media Items to None."""
        # General
        self._media_content_type = None
        self._media_title = None
        # TV Show
        self._media_episode = None
        self._media_season = None
        self._media_series_title = None 
        
        if plex_token:
            self._server = PlexServer(plex_url, plex_token)
        elif plex_user and plex_password:
            user = MyPlexAccount(plex_user, plex_password)
            server = plex_server if plex_server else user.resources()[0].name
            self._server = user.resource(server).connect()
        else:
            self._server = PlexServer(plex_url)
       
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update method for Plex sensor."""
        # new data refresh
        self._clear_server_details()

        self._sessions = self._server.sessions()
        media_attrs = {}
        for sess in self._sessions:
             self._session = sess
             self._sessioncount = self._sessioncount + 1
             session_id = 'session_' + str(self._sessioncount)
             self._session_type = self._session.type
             #  title (movie name, tv episode name, music song name)
             self._media_title = self._session.title
             # media type
             self._set_media_type()
             if self._session_type == 'episode':
               media_attrs[session_id] = sess.usernames[0] + ' - ' + self._media_series_title + " S" + self._media_season + "E" + self._media_episode + " - " + self._media_title
             else:
               media_attrs[session_id] = sess.usernames[0] + ' - ' + self._media_title

        if self._sessions is not None:
            self._state = self._sessioncount
            self._media_attrs = media_attrs
        else:
            self._state = 0

    def _clear_server_details(self):
        self._sessions = None
        self._sessioncount = 0
        self._media_attrs = {}
        """Set all Media Items to None."""
        # General
        self._media_content_type = None
        self._media_title = None
        # TV Show
        self._media_episode = None
        self._media_season = None
        self._media_series_title = None 

    def _set_media_type(self):
        if self._session_type in ['clip', 'episode']:
            self._media_content_type = MEDIA_TYPE_TVSHOW
            
            # season number (00)
            if callable(self._session.season):
                self._media_season = str(
                    (self._session.season()).index).zfill(2)
            elif self._session.parentIndex is not None:
                self._media_season = self._session.parentIndex.zfill(2)
            else:
                self._media_season = None
            # show name
            self._media_series_title = self._session.grandparentTitle
            # episode number (00)
            if self._session.index is not None:
                self._media_episode = str(self._session.index).zfill(2)
        
        elif self._session_type == 'movie':
            self._media_content_type = MEDIA_TYPE_VIDEO
            if self._session.year is not None and \
                    self._media_title is not None:
                self._media_title += ' (' + str(self._session.year) + ')'

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    
    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
    
    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._media_attrs
    
    @property
    def sessions(self):
        """Return the session, if any."""
        return self._sessions

    @property
    def sessioncount(self):
        """Return the session count, if any."""
        return self._sessioncount

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._media_attrs