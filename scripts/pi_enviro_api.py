#! /usr/bin/python
from flask import Flask
from pi_enviro import PiEnviro


# Initialize PiEnviro and API
pi_enviro = PiEnviro(influxdb_config='jwm_influxdb.yml') # initialize PiEnviro (using personal database)
pi_enviro_api = Flask(__name__)


@pi_enviro_api.route('/temp')
def temp():
    """
    API endpoint for '/temp'
    """
    return str(pi_enviro.get_temp())


@pi_enviro_api.route('/humidity')
def humidity():
    """
    API endpoint for '/humidity'
    """
    return str(pi_enviro.get_humidity())


@pi_enviro_api.route('/press')
def press():
    """
    API endpoint for '/press'
    """
    return str(pi_enviro.get_press())


if __name__ == '__main__':
    pi_enviro.run()
    pi_enviro_api.run(host='0.0.0.0')
    print('*** PiEnviroApi initialized! ***')
