#! /usr/bin/python
from flask import Flask
from pi_enviro import PiEnviro


# Initialize PiEnviro and API
pi_enviro = PiEnviro(influxdb_config='jwm_influxdb.yml') # initialize PiEnviro (using personal database)
rest_api = Flask(__name__)


@rest_api.route('/temp')
def temp():
    """
    API endpoint for '/temp'
    """
    return str(pi_enviro.get_temp())


@rest_api.route('/humidity')
def humidity():
    """
    API endpoint for '/humidity'
    """
    return str(pi_enviro.get_humidity())


@rest_api.route('/press')
def press():
    """
    API endpoint for '/press'
    """
    return str(pi_enviro.get_press())


if __name__ == '__main__':
    pi_enviro.run()
    rest_api.run(host='0.0.0.0')
    print('*** PiEnviroApi initialized! ***')
