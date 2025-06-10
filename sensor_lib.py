try:
    import bme680
except:
    pass


class FakeSensor:
    update = lambda self: None
    get_temperature = lambda self: 12.3
    get_pressure = lambda self: 990.0
    get_humidity = lambda self: 45.0


class Sensor:
    def __init__(self, offset=-5):
        try:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
        except (RuntimeError, IOError):
            self.sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)
        self.sensor.set_temp_offset(offset)

    def update(self):
        self.sensor.get_sensor_data()

    def get_temperature(self):
        return self.sensor.data.temperature

    def get_pressure(self):
        return self.sensor.data.pressure

    def get_humidity(self):
        return self.sensor.data.humidity
