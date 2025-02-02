from machine import I2C, Pin
import struct
import time

class BMP281:
    def __init__(self, i2c, address=0x76):
        self.i2c = i2c
        self.address = address
        self._read_calibration_data()
        self._configure_sensor()

    def _read_calibration_data(self):
        # Read temperature and pressure calibration data
        calib = self.i2c.readfrom_mem(self.address, 0x88, 24)
        self.dig_T1 = self._unpack_unsigned_short(calib[1], calib[0])
        self.dig_T2 = self._unpack_signed_short(calib[3], calib[2])
        self.dig_T3 = self._unpack_signed_short(calib[5], calib[4])

        self.dig_P1 = self._unpack_unsigned_short(calib[7], calib[6])
        self.dig_P2 = self._unpack_signed_short(calib[9], calib[8])
        self.dig_P3 = self._unpack_signed_short(calib[11], calib[10])
        self.dig_P4 = self._unpack_signed_short(calib[13], calib[12])
        self.dig_P5 = self._unpack_signed_short(calib[15], calib[14])
        self.dig_P6 = self._unpack_signed_short(calib[17], calib[16])
        self.dig_P7 = self._unpack_signed_short(calib[19], calib[18])
        self.dig_P8 = self._unpack_signed_short(calib[21], calib[20])
        self.dig_P9 = self._unpack_signed_short(calib[23], calib[22])

        # Read humidity calibration data if BME280
        try:
            self.dig_H1 = self.i2c.readfrom_mem(self.address, 0xA1, 1)[0]
            calib_h = self.i2c.readfrom_mem(self.address, 0xE1, 7)
            self.dig_H2 = self._unpack_signed_short(calib_h[1], calib_h[0])
            self.dig_H3 = calib_h[2]
            self.dig_H4 = (calib_h[3] << 4) | (calib_h[4] & 0x0F)
            self.dig_H5 = (calib_h[5] << 4) | (calib_h[4] >> 4)
            self.dig_H6 = calib_h[6]
            self.bme280 = True
        except:
            self.bme280 = False

    def _unpack_unsigned_short(self, b1, b2):
        return struct.unpack('>H', bytes([b1, b2]))[0]

    def _unpack_signed_short(self, b1, b2):
        return struct.unpack('>h', bytes([b1, b2]))[0]

    def _configure_sensor(self):
        # Configure the sensor (normal mode, temperature/pressure/humidity oversampling)
        self.i2c.writeto_mem(self.address, 0xF2, b'\x01' if self.bme280 else b'\x00')  # Humidity oversampling
        self.i2c.writeto_mem(self.address, 0xF4, b'\x27')  # Pressure and temp oversampling
        self.i2c.writeto_mem(self.address, 0xF5, b'\xA0')  # Standby time, filter

    def _read_raw_data(self):
        # Read raw temperature and pressure (and humidity if BME280) data
        data = self.i2c.readfrom_mem(self.address, 0xF7, 8 if self.bme280 else 6)
        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        adc_h = (data[6] << 8) | data[7] if self.bme280 else None
        return adc_t, adc_p, adc_h

    def _calculate_temperature(self, adc_t):
        var1 = (adc_t / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
        var2 = ((adc_t / 131072.0 - self.dig_T1 / 8192.0) * (adc_t / 131072.0 - self.dig_T1 / 8192.0)) * self.dig_T3
        self.t_fine = int(var1 + var2)
        temperature = (var1 + var2) / 5120.0
        return temperature

    def _calculate_pressure(self, adc_p):
        var1 = (self.t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0
        var2 = var2 + var1 * self.dig_P5 * 2.0
        var2 = (var2 / 4.0) + (self.dig_P4 * 65536.0)
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_P1
        if var1 == 0:
            return 0  # Avoid division by zero
        pressure = 1048576.0 - adc_p
        pressure = ((pressure - (var2 / 4096.0)) * 6250.0) / var1
        var1 = self.dig_P9 * pressure * pressure / 2147483648.0
        var2 = pressure * self.dig_P8 / 32768.0
        pressure = pressure + (var1 + var2 + self.dig_P7) / 16.0
        return pressure / 100.0  # Pressure in hPa

    def _calculate_humidity(self, adc_h):
        h = self.t_fine - 76800.0
        h = (adc_h - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h)) * (self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h * (1.0 + self.dig_H3 / 67108864.0 * h)))
        h = h * (1.0 - self.dig_H1 * h / 524288.0)
        return max(0, min(h, 100))  # Humidity in %

    def read_temperature(self):
        adc_t, _, _ = self._read_raw_data()
        return self._calculate_temperature(adc_t)

    def read_pressure(self):
        _, adc_p, _ = self._read_raw_data()
        return self._calculate_pressure(adc_p)

    def read_humidity(self):
        if not self.bme280:
            raise Exception("Humidity not supported on BMP280")
        _, _, adc_h = self._read_raw_data()
        return self._calculate_humidity(adc_h)

    def read_all(self):
        temperature = self.read_temperature()
        pressure = self.read_pressure()
        if self.bme280:
            humidity = self.read_humidity()
            return {
                'temperature': temperature,
                'pressure': pressure,
                'humidity': humidity
            }
        else:
            return {
                'temperature': temperature,
                'pressure': pressure
            }