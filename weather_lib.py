import time
import json
from urllib.request import urlopen
from datetime import datetime, timedelta

WEATHER_KEY = ''  # OpenWeatherMap API key
LOCATION_STRING = 'lat=50.24&lon=24.14' #'Velyki Mosty, UA'  # Location parameter, see below for details [50.2402, 24.1385]
# You can search for location with following ways:
# - By city name: city name and country code divided by comma, use ISO 3166 country codes. e.g. 'q=London,uk'
# - By city id: simply lookup your desired city in https://openweathermap.org/ and the city id will show up in URL field. e.g. 'id=2172797'
# - By geographic coordinates: by latitude and longitude. e.g. 'lat=35&lon=139'
# - By ZIP code: by zip/post code (if country is not specified, will search the USA). e.g. 'zip=94040,us'
UNIT_SUITE = 'metric'  # Unit of measurements, can be 'metric' or 'imperial'
TIME_UNIT = 24
# time_shift_s = 7200
time_shift_s = time.localtime().tm_gmtoff
WEATHER_URL = 'http://api.openweathermap.org/data/2.5/weather?APPID=' + WEATHER_KEY + '&units=' + UNIT_SUITE + '&' + LOCATION_STRING + '&lang=ua'
FORECAST_URL = 'http://api.openweathermap.org/data/2.5/forecast?APPID=' + WEATHER_KEY + '&units=' + UNIT_SUITE + '&' + LOCATION_STRING + '&lang=ua'

CLOUD_SUN_SIZE = {
    800: (0, 2),
    801: (1, 1),
    802: (2, 1),
    803: (3, 0),
    804: (4, 0)
}
# snow radius, snow number mask, rain radius, rain number mask, thunder
# mask:
#  1   4   2
#    8   16
RAIN_SNOW_SIZE = {
    600: (4, 7, 0, 0, False),
    601: (5, 7, 0, 0, False),
    602: (6, 31, 0, 0, False),
    611: (4, 3, 0, 0, False),
    612: (4, 7, 0, 0, False),
    613: (5, 7, 0, 0, False),
    615: (4, 2, 2, 1, False),
    616: (5, 7, 3, 24, False),
    620: (4, 3, 0, 0, False),
    621: (5, 7, 0, 0, False),
    622: (6, 31, 0, 0, False),
    500: (0, 0, 2, 7, False),
    501: (0, 0, 3, 7, False),
    502: (0, 0, 3, 31, False),
    503: (0, 0, 4, 31, False),
    504: (0, 0, 4, 31, False),
    511: (0, 0, 2, 31, False),
    520: (0, 0, 2, 3, False),
    521: (0, 0, 3, 7, False),
    522: (0, 0, 4, 31, False),
    531: (0, 0, 4, 31, False),
    300: (0, 0, 2, 3, False),
    301: (0, 0, 2, 3, False),
    302: (0, 0, 2, 31, False),
    310: (0, 0, 2, 7, False),
    311: (0, 0, 3, 7, False),
    312: (0, 0, 3, 31, False),
    313: (0, 0, 3, 7, False),
    314: (0, 0, 4, 31, False),
    321: (0, 0, 3, 7, False),
    200: (0, 0, 2, 3, True),
    201: (0, 0, 2, 3, True),
    202: (0, 0, 3, 27, True),
    210: (0, 0, 2, 3, True),
    211: (0, 0, 2, 3, True),
    212: (0, 0, 3, 27, True),
    221: (0, 0, 4, 27, True),
    230: (0, 0, 2, 3, True),
    231: (0, 0, 2, 3, True),
    232: (0, 0, 3, 27, True)
}


def utc_to_timezone(epoch):
    # TODO: check
    # return datetime.fromtimestamp(epoch) + timedelta(0, time_shift_s)
    return datetime.fromtimestamp(epoch)


class Forecast:
    def __init__(self, data):
        self.dt = utc_to_timezone(data['dt'])
        self.temperature = data['main']['temp']
        weather_list = data['weather']
        self.weather_ids = {w['id'] for w in weather_list}
        self.weather_icons = {w['icon'] for w in weather_list}
        self.snow_size = 0
        self.snow_mask = 0
        self.rain_size = 0
        self.rain_mask = 0
        self.thunder = False
        self.cloud_size = 0
        self.sun_size = 0
        rain_snow = self.weather_ids & set(RAIN_SNOW_SIZE.keys())
        if rain_snow:
            weather_id = next(iter(rain_snow))
            self.snow_size, self.snow_mask, self.rain_size, self.rain_mask, self.thunder = RAIN_SNOW_SIZE[weather_id]
            self.cloud_size = 4
        cloud_sun = self.weather_ids & set(CLOUD_SUN_SIZE.keys())
        if cloud_sun:
            weather_id = next(iter(cloud_sun))
            self.cloud_size, self.sun_size = CLOUD_SUN_SIZE[weather_id]


class Weather:
    def __init__(self, debug=False):
        self.debug = debug

    def update(self):
        if self.debug:
            with open('./weather_query.json') as f:
                weather_query = json.load(f)
            with open('./forecast_query.json') as f:
                forecast_query = json.load(f)
        else:
            with urlopen(WEATHER_URL) as weather_response:
                weather_query = json.loads(weather_response.read())
                # with open('weather_query.json', 'w', encoding='utf-8') as f:
                #     json.dump(weather_query, f, ensure_ascii=False, indent=4)
            with urlopen(FORECAST_URL) as forecast_response:
                forecast_query = json.loads(forecast_response.read())
                # with open('forecast_query.json', 'w', encoding='utf-8') as f:
                #     json.dump(forecast_query, f, ensure_ascii=False, indent=4)
        self.sunrise_time = utc_to_timezone(weather_query['sys']['sunrise'])
        self.sunset_time = utc_to_timezone(weather_query['sys']['sunset'])
        self.dt = utc_to_timezone(weather_query['dt'])
        self.humidity_now = weather_query['main']['humidity']
        self.pressure_now = int(weather_query['main']['pressure'] * 0.75006157584566)
        self.forecast_list = [Forecast(f) for f in forecast_query['list']]
        # print(self.dt, self.sunrise_time, self.sunset_time)


if __name__ == "__main__":
    w = Weather(True)
    w.update()
    print(w.sunrise_time, w.sunset_time)
    print(json.dumps(forecast_query, indent=4))
