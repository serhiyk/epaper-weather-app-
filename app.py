#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import time
import random
import locale
import math
import urllib.request
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageChops
from weather_lib import Weather
from moon_lib import phase_of_moon
try:
    import epd7in5_V2
except:
    print('EPD library error')
import sensor_lib


def rotate_point(x, y, centre_x, centre_y, angle):
    angle = math.radians(angle)
    new_x = centre_x + math.cos(angle) * (x - centre_x) - math.sin(angle) * (y - centre_y)
    new_y = centre_y + math.sin(angle) * (x - centre_x) + math.cos(angle) * (y - centre_y)
    return new_x, new_y


def rotate_polygon(xy, centre_x, centre_y, angle):
    return [rotate_point(x, y, centre_x, centre_y, angle) for x, y in xy]


def parse_range(s):
    start, *end = s.split('-')
    end = end[0] if end else start
    return int(start), int(end) + 1


class FakeEpd:
    init = lambda self: None
    Clear = lambda self: None
    init_fast = lambda self: None
    sleep = lambda self: None
    display = lambda self, data: None
    width = 800
    height = 480

    def getbuffer(self, data):
        data.save('out.png')


class DrawWrapper:
    def __init__(self, img):
        self.draw = ImageDraw.Draw(img)

    def __getattr__(self, attr):
        return getattr(self.draw, attr)

    def write_text(self, text, font, x, y, w=None, h=None):
        if w or h:
            left, top, right, bottom = font.getbbox(text)
            if w:
                x += (w - (right - left)) // 2
            if h:
                y += (h - (bottom - top)) // 2
        self.draw.text((x, y), text, font=font, fill=0)

    def write_sun(self, x, y, r):
        self.draw.circle((x, y), r, width=2)
        ray = ((x - 1, y - r * 1.8), (x + 1, y - r * 1.8), (x + 1, y - r - 3), (x - 1, y - r - 3))
        for angle in range(0, 360, 30):
            xy = rotate_polygon(ray, x, y, angle)
            self.draw.polygon(xy, width=1)

    def write_moon(self, x, y, r):
        phase_angle = phase_of_moon(50.24, 24.14, datetime.now())
        self.draw.circle((x, y), r, fill=0)
        if phase_angle < 90:
            self.draw.circle((x-r/2, y), r, fill=1)
        elif phase_angle < 270:
            self.draw.rectangle(((x - r, y - r), (x, y + r)), fill=1)
        self.draw.circle((x, y), r, width=1)

    def write_cloud(self, x, y, width, fill=False):
        r1 = width / 4
        r2 = width / 6
        r3 = width / 8
        cloud_width = 3
        cloud_width = width / 20
        self.draw.circle((x + r1 + r2 * 1.2, y - r1), r1, fill=0)
        self.draw.circle((x + r2, y - r2), r2, fill=0)
        self.draw.circle((x + width - r3, y - r3), r3, fill=0)
        self.draw.circle((x + width - r3 * 2, y - r3 * 1.5), r3, fill=0)
        self.draw.rectangle(((x + r2, y - r3 * 2), (x + width - r3, y)), fill=0)
        if not fill:
            self.draw.circle((x + r1 + r2 * 1.2, y - r1), r1 - cloud_width, fill=1)
            self.draw.circle((x + r2, y - r2), r2 - cloud_width, fill=1)
            self.draw.circle((x + width - r3, y - r3), r3 - cloud_width, fill=1)
            self.draw.circle((x + width - r3 * 2, y - r3 * 1.5), r3 - cloud_width, fill=1)
            self.draw.rectangle(((x + r2, y - r3 * 1.5), (x + width - r3, y - cloud_width)), fill=1)

    def write_rain(self, x, y, r):
        self.draw.circle((x, y), r)
        self.draw.polygon(((x - r, y), (x, y - r * 2), (x + r, y)), fill=0)

    def write_snow(self, x, y, r):
        ray = ((x, y - r), (x, y + r))
        for angle in range(0, 360, 120):
            xy = rotate_polygon(ray, x, y, angle)
            self.draw.line(xy)

    def write_thunder(self, x, y):
        d = 5
        points = (
            (x, y),
            (x - d, y),
            (x, y - d * 4),
            (x + d, y - d * 4),
            (x + d / 2, y - d),
            (x + d * 1.5, y - d),
            (x - d / 2, y + d * 3))
        self.draw.polygon(points, fill=1)
        self.draw.polygon(points)


class App:
    FORECAST_NUM = 9

    def __init__(self):
        try:
            self.epd = epd7in5_V2.EPD()
        except:
            print('Fake EPD is using')
            self.epd = FakeEpd()
        try:
            self.sensor = sensor_lib.Sensor()
        except:
            print('Fake Sensor is using')
            self.sensor = sensor_lib.FakeSensor()
        self.imgs = {}
        for root, _, files in os.walk('./img/'):
            for file in files:
                if not file.endswith('.png'):
                    continue
                img = Image.open(root + '/' + file)
                m, d, *_ = file.split('_')
                for i in range(*parse_range(m)):
                    imgs_m = self.imgs.get(i, {})
                    if not imgs_m:
                        self.imgs[i] = imgs_m
                    for j in range(*parse_range(d)):
                        imgs_d = imgs_m.get(j, [])
                        if not imgs_d:
                            imgs_m[j] = imgs_d
                        imgs_d.append(img)

        self.epd.init()
        self.epd.Clear()
        self.font16 = ImageFont.truetype('./Academy.ttf', 16)
        self.font64 = ImageFont.truetype('./Academy.ttf', 64)
        self.font128 = ImageFont.truetype('./Academy.ttf', 128)
        self.font256 = ImageFont.truetype('./Academy.ttf', 256)
        self.weather_image = None
        self.himage = None
        self.draw = None
        self.weather = Weather()
        self.update_weather()
        self.new_frame()
        self.write_text('ІНІЦІАЛІЗАЦІЯ', self.font64, 0, 0, self.epd.width, self.epd.height)
        self.update()

    def write_all(self):
        self.new_frame()
        self.write_img()
        self.write_time()
        self.write_weather()
        self.write_sensors()
        self.write_sensors_ext()
        self.update()

    def new_frame(self):
        self.himage = Image.new('1', (self.epd.width, self.epd.height), 255)  # 255: clear the frame
        self.draw = ImageDraw.Draw(self.himage)

    def update(self):
        self.epd.init_fast()
        self.epd.display(self.epd.getbuffer(self.himage))
        self.epd.sleep()

    def write_text(self, text, font, x, y, w=None, h=None):
        if w or h:
            left, top, right, bottom = font.getbbox(text)
            if w:
                x += (w - (right - left)) // 2
            if h:
                y += (h - (bottom - top)) // 2
        self.draw.text((x, y), text, font=font, fill=0)

    def write_time(self):
        text = time.strftime('%H:%M')
        self.write_text(text, self.font256, 0, 90, self.epd.width)

    def write_dow(self):
        text = time.strftime('%A')
        self.write_text(text, self.font128, 0, 300, self.epd.width)

    def write_img(self):
        imgs_m = self.imgs.get(time.localtime().tm_mon, self.imgs.get(0, {}))
        imgs_d = imgs_m.get(time.localtime().tm_mday, imgs_m.get(0, []))
        if imgs_d:
            self.himage.paste(random.choice(imgs_d), (0, self.epd.height - 250))

    def update_weather(self):
        half_period = 90
        width = self.epd.width // self.FORECAST_NUM
        height = 90
        header_offset = 14
        sun_r = 12
        sun_small_r = 10
        moon_r = 20
        moon_small_r = 16
        cloud_offset = header_offset + sun_r * 2 + moon_r
        self.weather.update()
        sunrise_time = self.weather.sunrise_time.hour * 60 + self.weather.sunrise_time.minute
        sunset_time = self.weather.sunset_time.hour * 60 + self.weather.sunset_time.minute
        self.weather_image = Image.new('1', (self.epd.width, height), 255)
        draw = DrawWrapper(self.weather_image)
        night_img = Image.new('1', (self.epd.width, height), 0)
        night_draw = DrawWrapper(night_img)
        for i, w in enumerate(self.weather.forecast_list[:self.FORECAST_NUM]):
            forecast_time = w.dt.hour * 60 + w.dt.minute
            is_daytime = sunrise_time <= forecast_time <= sunset_time
            time_str = w.dt.strftime('%H:%M')
            draw.write_text(time_str, self.font16, width * i, 1, width)
            draw.write_text(f'{int(w.temperature)}°', self.font16, width * i + 4, header_offset + 2)
            width_center = width * i + width // 2
            if w.sun_size == 2:
                if is_daytime:
                    draw.write_sun(width * i + width // 2, header_offset + sun_r * 2, sun_r)
                else:
                    draw.write_moon(width * i + width // 2, header_offset + sun_r * 2, moon_r)
            elif w.sun_size == 1:
                if is_daytime:
                    draw.write_sun(width * i + width * 2 // 3, header_offset + sun_small_r * 2, sun_small_r)
                else:
                    draw.write_moon(width * i + width * 2 // 3, header_offset + sun_small_r * 2, moon_small_r)
            if w.cloud_size:
                cloud_width = width * [0, 0.3, 0.5, 0.7, 0.8, 0.8][w.cloud_size]
                draw.write_cloud(width * i + (width - cloud_width) // 2, cloud_offset, cloud_width, w.cloud_size == 5)
            if w.rain_mask & 4:
                draw.write_rain(width_center, cloud_offset + 10, w.rain_size)
            if w.rain_mask & 1:
                draw.write_rain(width_center - w.rain_size * 4, cloud_offset + 10, w.rain_size)
            if w.rain_mask & 2:
                draw.write_rain(width_center + w.rain_size * 4, cloud_offset + 10, w.rain_size)
            if w.rain_mask & 8:
                draw.write_rain(width_center - w.rain_size * 2, cloud_offset + 10 + w.rain_size * 4, w.rain_size)
            if w.rain_mask & 16:
                draw.write_rain(width_center + w.rain_size * 2, cloud_offset + 10 + w.rain_size * 4, w.rain_size)
            if w.snow_mask & 4:
                draw.write_snow(width_center, cloud_offset + 10, w.snow_size)
            if w.snow_mask & 1:
                draw.write_snow(width_center - w.snow_size * 4, cloud_offset + 10, w.snow_size)
            if w.snow_mask & 2:
                draw.write_snow(width_center + w.snow_size * 4, cloud_offset + 10, w.snow_size)
            if w.snow_mask & 8:
                draw.write_snow(width_center - w.snow_size * 2, cloud_offset + 10 + w.snow_size * 2, w.snow_size)
            if w.snow_mask & 16:
                draw.write_snow(width_center + w.snow_size * 2, cloud_offset + 10 + w.snow_size * 2, w.snow_size)
            if w.thunder:
                draw.write_thunder(width * i + width // 2, cloud_offset)
            if forecast_time + half_period <= sunrise_time or forecast_time - half_period >= sunset_time:
                night_draw.rectangle(((width * i, 0), (width * (i + 1), header_offset - 1)), fill=1)
            elif forecast_time - half_period < sunrise_time < forecast_time + half_period:
                part_width = (sunrise_time - (forecast_time - half_period)) * width // 180
                night_draw.rectangle(((width * i, 0), (width * i + part_width, header_offset - 1)), fill=1)
            elif forecast_time - half_period < sunset_time < forecast_time + half_period:
                part_width = (sunset_time - (forecast_time - half_period)) * width // 180
                night_draw.rectangle(((width * i + part_width, 0), (width * (i + 1), header_offset - 1)), fill=1)

        self.weather_image = ImageChops.logical_xor(self.weather_image, night_img)

    def write_weather(self):
        self.himage.paste(self.weather_image, (0, 0))

    def write_sensors(self):
        self.sensor.update()
        temperature = self.sensor.get_temperature()
        text = f'{temperature:.1f}°'
        self.write_text(text, self.font64, 5, 90)
        humidity = int(self.sensor.get_humidity())
        pressure = int(self.sensor.get_pressure() * 0.750061683)
        text = f'{humidity}%    {pressure}'
        self.write_text(text, self.font16, 15, 145)

    def write_sensors_ext(self):
        try:
            with urllib.request.urlopen('http://192.168.0.109/temperaturec', timeout=2) as response:
                html_content = response.read()
                temperature = float(html_content)
                text = f'{temperature:.1f}°'
                self.write_text(text, self.font64, 5, 170)
        except urllib.error.URLError as e:
            print(f"Error accessing the URL: {e.reason}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, 'uk_UA.UTF-8')
    time.sleep(1)
    app = App()
    try:
        while True:
            curr_sec = time.localtime().tm_sec
            sleep_sec = 60 - curr_sec
            time.sleep(sleep_sec)
            if time.localtime().tm_min == 1:
                app.update_weather()
            app.write_all()
    except KeyboardInterrupt:
        pass
    finally:
        epd7in5_V2.epdconfig.module_exit(cleanup=True)
