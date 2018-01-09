#! /usr/bin/python
from datetime import datetime
from netifaces import ifaddresses, AF_INET
from os import popen
from os.path import dirname, join
from pint import UnitRegistry
from pint.converters import ScaleConverter
from pint.unit import UnitDefinition
from requests import post
from requests.exceptions import ConnectionError
from sense_hat import SenseHat
from threading import Thread
from time import sleep
from yaml import load


class PiEnviro(object):
    """
    Class that interfaces with the Pi Sense HAT to collect environment
    data from the onboard sensors, post data to the onboard screen, and
    if configured post data to an InfluxDB database.
    """

    # Colors (R,G,B)
    pink = (215, 25, 139)
    black = (0, 0, 0)

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
        self._temp_thread_obj = self._init_temp_thread()
        self._humidity_thread_obj = self._init_humidity_thread()
        self._press_thread_obj = self._init_press_thread()
        if influxdb_config: self._influxdb_thread_obj = self._init_influxdb_thread(influxdb_config) # only initialize this thread if config is passed in

    def _init_defaults(self):
        """
        Initialize default values.
        """
        # Initialize unit registry, percent unit (for humidity)
        self._ureg = UnitRegistry()
        self._ureg.define(UnitDefinition('%', 'pct', (), ScaleConverter(1/100.0)))
        # Initialize timing defaults
        self._read_temp_wait_sec = 15.0
        self._read_humidity_wait_sec = 15.0
        self._read_press_wait_sec = 15.0
        self._post_influxdb_wait_sec = 60.0
        # Initialize screen defaults
        self._screen_message = 'Hello World!'
        self._screen_speed = 0.1
        self._screen_text_color = self.pink
        self._screen_background_color = self.black

    def _init_sense_hat(self):
        """
        Initialize connection with Sense HAT.
        """
        # Initialize SenseHat object
        self._sense_hat = SenseHat()
        self._sense_hat.low_light = True # make screen a little dimmer
        self._sense_hat.set_rotation(180) # set rotation for horizontal, with power supple in the back
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

    def _generate_screen_message(self):
        """
        Generate and return screen message.
        """
        return 'Temperature: {:.2f}, Humidity: {:.2f}, Pressure: {:.2f}'.format(self.curr_temp.to('degF'), self.curr_humidity, self.curr_press.to('inHg'))

    ####################################################################

    def get_temp(self, force_update=False):
        """
        Get current temperature reading, in degF.
        :param force_update: Force update before return.
        """
        if force_update: self._update_temp()
        return self.curr_temp.to('degF').magnitude # return as float using units degF

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

    def _read_temp(self, calibrate_temp=True):
        """
        Query and return current temperature.
        :param calibrate_temp: If True will also query CPU temperature
        and use this to return calibrated temperature, not raw sensor
        temperature.
        """
        raw_temp = self._ureg.Quantity(self._sense_hat.get_temperature(), 'degC')
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
        return self._ureg.Quantity(rtn_float, 'degC')

    ####################################################################

    def get_humidity(self, force_update=False):
        """
        Get current humidity reading, in %.
        :param force_update: Force update before return.
        """
        if force_update: self._update_humidity()
        return self.curr_humidity.magnitude # return as flaot

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

    def _read_humidity(self):
        """
        Query and return current humidity.
        """
        return self._ureg.Quantity(self._sense_hat.get_humidity(), 'pct')

    ####################################################################

    def get_press(self, force_update=False):
        """
        Get current pressure reading, in inHg.
        :param force_update: Force update before return.
        """
        if force_update: self._update_press()
        return self.curr_press.to('inHg').magnitude # return as float using units inHg

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

    def _read_press(self):
        """
        Query and return current pressure.
        """
        return self._ureg.Quantity(self._sense_hat.get_pressure(), 'mbar')

    ####################################################################

    def generate_influxdb_post_url(self, influxdb_config):
        '''
        Read config file to generate and return InfluxDB POST URL.
        :param influxdb_config: String containing InfluxDB config
        filename, which should be located in /scripts directory.
        '''
        post_url=''
        with open(join(dirname(__file__), influxdb_config)) as config_file:
            try:
                config = load(config_file) # expected: url, db -- optional: username, password
                if 'username' in config and 'password' in config:
                    post_url = '{url}/write?db={db}&u={username}&p={password}'.format(url=config['url'], db=config['db'], username=config['username'], password=config['password'])
                else: # no credentials needed
                    post_url = '{url}/write?db={db}'.format(url=config['url'], db=config['db'])
            except yaml.YAMLError as err:
                logging.fatal('Could not create InfluxDB post url path, invalid config file found (config: {config_path})'.format(config_path=influxdb_config))
        print('Generated InfluxDB POST URL: {}'.format(post_url))
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
        post_url = self.generate_influxdb_post_url(influxdb_config) # only need to generate this once
        while True:
            try:
                post_data = 'env_data[{}] temp={},humidity={},press={}'.format(self._get_ipaddr(), self.get_temp(), self.get_humidity(), self.get_press())
                post_resp = post(post_url, data=post_data)
            except ConnectionError as CE:
                with open('/app/resp.log', 'a+') as outfile:
                    outfile.write('{} Connection Error: {} {} {}\n'.format(str(datetime.now()), CE, CE.errno, CE.strerror))
                print('{} Failed to post InfluxDB update to "env_data" series, response: {}'.format(str(datetime.now()), post_resp))
                continue
            sleep(self._post_influxdb_wait_sec)

    def _get_ipaddr(self):
        """
        Query and return current IP address.
        TODO: Allow dynamic determination of hardcoded "eth0" internet interface
        """
        return ifaddresses('eth0')[AF_INET][0]['addr'] # physical ethernet cable


if __name__ == '__main__':
    pi = PiEnviro(influxdb_config='jwm_influxdb.yml') # initialize PiEnviro (using personal database)
    pi.run()
    print('*** PiEnviro initialized! ***')
