#!/usr/bin/python
from datetime import datetime
from netifaces import ifaddresses, AF_INET
from os import popen
from os.path import dirname, join
#FIXME from pint import UnitRegistry
#FIXME from pint.converters import ScaleConverter
#FIXME from pint.unit import UnitDefinition
#FIXME from requests import post
#FIXME from requests.exceptions import ConnectionError, MissingSchema
from sense_hat import SenseHat
from threading import Thread
from time import sleep
#FIXME from yaml import load, YAMLError

# TODO: Remove InfluxDB stuff and put in separate class, which can call PiEnviro getters to post to database


class PiEnviro(object):
    """
    Class that interfaces with the Pi Sense HAT to collect environment
    data from the onboard sensors, post data to the onboard screen, and
    if configured post data to an InfluxDB database.
    """

    # Colors (R,G,B)
    colors = [(0,0,0),        # black
              (255,255,255),  # white
              (255,0,0),      # red
              (0,255,0),      # lime
              (0,0,255),      # blue
              (255,255,0),    # yellow
              (0,255,255),    # cyan / aqua
              (255,0,255)]    # magenta / fuchsia

    screen_rotations = [0,    # power forward
                        90,   # power right
                        180,  # power back
                        270]  # power left

    # Scroll speeds (lower is faster)
    scroll_speeds = [0.15, 0.125, 0.1, 0.075, 0.05]

    # Environment data
    curr_temp = None
    curr_humidity = None
    curr_press = None

    ####################################################################

    def __init__(self, influxdb_config=None):
        """
        Constructor.
        :param influxdb_config: String containing InfluxDB config
        filename, which should be located in /scripts directory.
        """
        self._init_defaults()
        self._init_sense_hat()
        # Initialize control threads
        self._screen_thread_obj = self._init_screen_thread()
        self._joystick_thread_obj = self._init_joystick_thread()
        self._temp_thread_obj = self._init_temp_thread()
        self._humidity_thread_obj = self._init_humidity_thread()
        self._press_thread_obj = self._init_press_thread()
        if influxdb_config: self._influxdb_thread_obj = self._init_influxdb_thread(influxdb_config) # only initialize this thread if config is passed in

    def _init_defaults(self):
        """
        Initialize default values.
        """
        # Initialize unit registry, percent unit (for humidity)
        #FIXME self._ureg = UnitRegistry()
        #FIXME self._ureg.define(UnitDefinition('%', 'pct', (), ScaleConverter(1/100.0)))
        # Initialize timing defaults
        self._read_temp_wait_sec = 15.0
        self._read_humidity_wait_sec = 15.0
        self._read_press_wait_sec = 15.0
        self._post_influxdb_wait_sec = 60.0
        # Initialize screen defaults
        self._screen_rotation = self.screen_rotations[3]
        self._screen_message = '' # This is set by _update_screen_message
        self._screen_speed_index = 2 # middle
        self._screen_speed = self.scroll_speeds[self._screen_speed_index]
        self._screen_text_color_index = 4 # blue
        self._screen_text_color = self.colors[self._screen_text_color_index]
        self._screen_background_color = self.colors[0] # black

    def _init_sense_hat(self):
        """
        Initialize connection with Sense HAT.
        """
        # Initialize SenseHat object
        self._sense_hat = SenseHat()
        self._sense_hat.low_light = True # make screen a little dimmer
        self._sense_hat.set_rotation(self._screen_rotation)
        # Initialize environment defaults
        self.curr_temp = self._read_temp()
        self.curr_humidity = self._read_humidity()
        self.curr_press = self._read_press()

    ####################################################################

    def run(self):
        """
        Run application, which starts all initialized threads.
        """
        self._screen_thread_obj.start()
        self._joystick_thread_obj.start()
        self._temp_thread_obj.start()
        self._humidity_thread_obj.start()
        self._press_thread_obj.start()
        if hasattr(self, '_influxdb_thread_obj'): self._influxdb_thread_obj.start() # only start this thread if it was initialized

    ####################################################################

    def _init_screen_thread(self, start_thread=False):
        """
        Initialize screen update thread and return it.
        :param start_thread: If True will also start thread.
        """
        screen_thread = Thread(target=self._screen_thread)
        if start_thread: screen_thread.start()
        return screen_thread

    def _screen_thread(self):
        """
        Screen update thread loop.
        """
        while True:
            self._update_screen_message()
            self._sense_hat.show_message(self._screen_message, self._screen_speed, self._screen_text_color, self._screen_background_color)

    def _update_screen_message(self):
        """
        Generate and save screen message.
        """
        self._screen_message = self._generate_screen_message()
        print('Screen message updated to "{}"'.format(self._screen_message))

    def _generate_screen_message(self):
        """
        Generate and return screen message.
        """
        #FIXME screen_message = 'Temp: {:.1f}, Humidity: {:.1f}, Press: {:.2f}'.format(self.curr_temp.to('degF'), self.curr_humidity, self.curr_press.to('inHg'))
        #FIXME screen_message = screen_message.replace('_', '') # strip '_' from 'in_Hg' -- this can be removed if pint updates to output string as 'inHg' instead of inserting the extra '_'
        screen_message = 'Temp: {:.1f} degF, Humidity: {:.1f} %, Press: {:.2f} inHg'.format(self.curr_temp, self.curr_humidity, self.curr_press)
        return screen_message

    ####################################################################

    def inc_screen_color(self):
        """
        Increment screen color to next highest value in self.colors
        list. Loop when necessary.
        """
        self._screen_text_color_index += 1
        try:
            self._screen_text_color = self.colors[self._screen_text_color_index]
        except IndexError: # loop
            self._screen_text_color_index = 0
            self._screen_text_color = self.colors[self._screen_text_color_index]
        print('Screen color changed to {}'.format(self._screen_text_color))
        self._sense_hat.clear(self._screen_text_color) # flash current color for feedback (scrolling text will overwrite it immediately)

    def dec_screen_color(self):
        """
        Decrement screen color to next highest value in self.colors
        list. Loop when necessary.
        """
        self._screen_text_color_index -= 1
        try:
            self._screen_text_color = self.colors[self._screen_text_color_index]
        except IndexError: # loop
            self._screen_text_color_index = len(self.colors) - 1 # max
            self._screen_text_color = self.colors[self._screen_text_color_index]
        print('Screen color changed to {}'.format(self._screen_text_color))
        self._sense_hat.clear(self._screen_text_color) # flash current color for feedback (scrolling text will overwrite it immediately)

    def inc_screen_speed(self):
        """
        Increment screen text scroll speed to next highest value in
        self.scroll_speeds list. Don't loop.
        """
        self._screen_speed_index += 1
        try:
            self._screen_speed = self.scroll_speeds[self._screen_speed_index]
        except IndexError: # loop
            self._screen_speed_index = len(self.scroll_speeds) - 1 # max
            self._screen_speed = self.scroll_speeds[self._screen_speed_index]
        print('Screen speed changed to {}'.format(self._screen_speed))
        self._sense_hat.clear(self._screen_text_color) # flash current color for feedback (scrolling text will overwrite it immediately)

    def dec_screen_speed(self):
        """
        Decrement screen text scroll speed to next highest value in
        self.scroll_speeds list. Don't loop.
        """
        self._screen_speed_index -= 1
        try:
            self._screen_speed = self.scroll_speeds[self._screen_speed_index]
        except IndexError: # loop
            self._screen_speed_index = 0
            self._screen_speed = self.scroll_speeds[self._screen_speed_index]
        print('Screen speed changed to {}'.format(self._screen_speed))
        self._sense_hat.clear(self._screen_text_color) # flash current color for feedback (scrolling text will overwrite it immediately)

    def _init_joystick_thread(self, start_thread=False):
        """
        Initialize joystick input thread and return it.
        :param start_thread: If True will also start thread.
        """
        joystick_thread = Thread(target=self._joystick_thread)
        if start_thread: joystick_thread.start()
        return joystick_thread

    def _joystick_thread(self):
        """
        Joystick input thread loop.
        NOTES ON API:
        A tuple describing a joystick event. Contains three named parameters:
        timestamp - The time at which the event occurred, as a fractional number of seconds (the same format as the built-in time function)
        direction - The direction the joystick was moved, as a string ("up", "down", "left", "right", "middle")
        action - The action that occurred, as a string ("pressed", "released", "held")
        """
        while True:
            event = self._sense_hat.stick.wait_for_event()
            print('Detected joystick event: {} was {} at {}'.format(event.action, event.direction, event.timestamp))
            if event.action == "pressed":
                if event.direction == "up": # TODO: handle correct joystick orientation per self._screen_rotation
                    self.inc_screen_color()
                elif event.direction == "down":
                    self.dec_screen_color()
                elif event.direction == "left":
                    self.inc_screen_speed()
                elif event.direction == "right":
                    self.dec_screen_speed()
                else:
                    print('Unrecognized direction!')
            else:
                print('Ignoring event ...')

    ####################################################################

    def get_temp(self, force_update=False):
        """
        Get current temperature reading, in degF.
        :param force_update: Force update before return.
        """
        if force_update: self._update_temp()
        return self.curr_temp #FIXME self.curr_temp.to('degF').magnitude # return as float using units degF

    def _init_temp_thread(self, start_thread=False):
        """
        Initialize temperature update thread and return it.
        :param start_thread: If True will also start thread.
        """
        temp_thread = Thread(target=self._temp_thread)
        if start_thread: temp_thread.start()
        return temp_thread

    def _temp_thread(self):
        """
        Temperature update thread loop.
        """
        while True:
            self._update_temp()
            sleep(self._read_temp_wait_sec)

    def _update_temp(self):
        """
        Query and save current temperature.
        """
        self.curr_temp = self._read_temp()
        #FIXME print('Updated current temperature to {:.1f}'.format(self.curr_temp.to('degF')))
        print('Updated current temperature to {:.1f}'.format(self.curr_temp))

    def _read_temp(self, calibrate_temp=False): # FIXME: Calibrate should default to True
        """
        Query and return current temperature.
        :param calibrate_temp: If True will also query CPU temperature
        and use this to return calibrated temperature, not raw sensor
        temperature.
        """
        raw_temp = self._sense_hat.get_temperature() * 1.8 + 32 #FIXME self._ureg.Quantity(self._sense_hat.get_temperature(), 'degC')
        if calibrate_temp:
            return raw_temp - ((self._read_cpu_temp() - raw_temp) / 1.556) # https://github.com/initialstate/wunderground-sensehat/wiki/Part-3.-Sense-HAT-Temperature-Correction
        else:
            return raw_temp

    def _read_cpu_temp(self):
        """
        Query and return current CPU temperature.
        """
        rtn_str = popen('vcgencmd measure_temp').readline() # rtn in the format of: temp=41.7'C
        rtn_float = float(rtn_str.replace("temp=","").replace("'C\n","")) # rtn in the format of: 41.7
        return rtn_float * 1.8 + 32 #FIXME self._ureg.Quantity(rtn_float, 'degC')

    ####################################################################

    def get_humidity(self, force_update=False):
        """
        Get current humidity reading, in %.
        :param force_update: Force update before return.
        """
        if force_update: self._update_humidity()
        return self.curr_humidity #FIXME self.curr_humidity.magnitude # return as flaot

    def _init_humidity_thread(self, start_thread=False):
        """
        Initialize humidity update thread and return it.
        :param start_thread: If True will also start thread.
        """
        humidity_thread = Thread(target=self._humidity_thread)
        if start_thread: humidity_thread.start()
        return humidity_thread

    def _humidity_thread(self):
        """
        Humidity update thread loop.
        """
        while True:
            self._update_humidity()
            sleep(self._read_humidity_wait_sec)

    def _update_humidity(self):
        """
        Query and save current humidity.
        """
        self.curr_humidity = self._read_humidity()
        print('Updated current humidity to {:.1f}'.format(self.curr_humidity))

    def _read_humidity(self):
        """
        Query and return current humidity.
        """
        return self._sense_hat.get_humidity() # FIXME self._ureg.Quantity(self._sense_hat.get_humidity(), 'pct')

    ####################################################################

    def get_press(self, force_update=False):
        """
        Get current pressure reading, in inHg.
        :param force_update: Force update before return.
        """
        if force_update: self._update_press()
        return self.curr_press #FIXME self.curr_press.to('inHg').magnitude # return as float using units inHg

    def _init_press_thread(self, start_thread=False):
        """
        Initialize pressure update thread and return it.
        :param start_thread: If True will also start thread.
        """
        press_thread = Thread(target=self._press_thread)
        if start_thread: press_thread.start()
        return press_thread

    def _press_thread(self):
        """
        Pressure update thread loop.
        """
        while True:
            self._update_press()
            sleep(self._read_press_wait_sec)

    def _update_press(self):
        """
        Query and save current pressure.
        """
        self.curr_press = self._read_press()
        #FIXME print('Updated current pressure to {:.2f}'.format(self.curr_press.to('inHg')))
        print('Updated current pressure to {:.2f}'.format(self.curr_press))

    def _read_press(self):
        """
        Query and return current pressure.
        """
        return self._sense_hat.get_pressure() * 0.02953 # FIXME self._ureg.Quantity(self._sense_hat.get_pressure(), 'mbar')

    ####################################################################

    def generate_influxdb_post_url(self, influxdb_config):
        '''
        Read config file to generate and return InfluxDB POST URL.
        :param influxdb_config: String containing InfluxDB config
        filename, which should be located in /scripts directory.
        '''
        post_url=''
        # FIXME try:
        # FIXME     with open(join(dirname(__file__), influxdb_config)) as config_file:
        # FIXME         config = load(config_file) # expected: url, db -- optional: username, password
        # FIXME         if 'username' in config and 'password' in config:
        # FIXME             post_url = '{url}/write?db={db}&u={username}&p={password}'.format(url=config['url'], db=config['db'], username=config['username'], password=config['password'])
        # FIXME         else: # no credentials needed
        # FIXME             post_url = '{url}/write?db={db}'.format(url=config['url'], db=config['db'])
        # FIXME except (IOError, YAMLError) as err:
        # FIXME     print('Could not create InfluxDB post url path, invalid config file ({})!'.format(influxdb_config))
        # FIXME print('Generated InfluxDB post url: {}'.format(post_url))
        return post_url

    def _init_influxdb_thread(self, influxdb_config, start_thread=False):
        """
        Initialize InfluxDB update thread and return it.
        :param influxdb_config: String containing InfluxDB config
        filename, which should be located in /scripts directory.
        :param start_thread: If True will also start thread.
        """
        influxdb_thread = Thread(target=self._influxdb_thread, args=[influxdb_config])
        if start_thread: influxdb_thread.start()
        return influxdb_thread

    def _influxdb_thread(self, influxdb_config):
        """
        InfluxDB update thread loop.
        :param influxdb_config: String containing InfluxDB config
        filename, which should be located in /scripts directory.
        """
        pass #FIXME 
        # FIXME post_url = self.generate_influxdb_post_url(influxdb_config) # only need to generate this once
        #FIXME while True:
        #FIXME     try:
        #FIXME         post_data = 'env_data[{}] temp={},humidity={},press={}'.format(self._get_ipaddr(), self.get_temp(), self.get_humidity(), self.get_press())
        #FIXME         post_resp = post(post_url, data=post_data)
        #FIXME     except (ConnectionError, MissingSchema):
        #FIXME         print('{} Failed to post InfluxDB update to "env_data" series!'.format(str(datetime.now())))
        #FIXME     sleep(self._post_influxdb_wait_sec)

    def _get_ipaddr(self):
        """
        Query and return current IP address.
        """
        # prefer ethernet ip_addr (if available)
        try:
            return ifaddresses('eth0')[AF_INET][0]['addr'] # physical ethernet cable
        except KeyError:
            print('Unable to determine ip_addr from ethernet connection')
        # use wifi ip_addr if no ethernet
        try:
            return ifaddresses('wlan0')[AF_INET][0]['addr'] # wifi connection
        except KeyError:
            print('Unable to determine ip_addr from WiFi connection')
        # no connection
        return ''


if __name__ == '__main__':
    pi = PiEnviro()
    pi.run()
    print('*** PiEnviro initialized! ***')
