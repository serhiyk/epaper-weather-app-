import math
from datetime import datetime


def phase_of_moon(latitude, longitude, date):
    # Convert date to Julian date
    jd = (date - datetime(2000, 1, 1)).total_seconds() / 86400 + 2451545.0

    # Calculate the moon's mean longitude
    L = (218.316 + 13.176396 * jd) % 360

    # Calculate the moon's mean anomaly
    M = (134.963 + 13.064993 * jd) % 360

    # Calculate the moon's argument of latitude
    F = (93.272 + 13.229350 * jd) % 360

    # Calculate the moon's ecliptic latitude and longitude
    l = L + 6.289 * math.sin(math.radians(M))
    b = 5.128 * math.sin(math.radians(F))
    r = 385001 - 20905 * math.cos(math.radians(M))

    # Calculate the moon's equatorial coordinates
    obl = 23.439 - 0.0000004 * jd
    x = r * math.cos(math.radians(l))
    y = r * math.cos(math.radians(obl)) * math.sin(math.radians(l))
    z = r * math.sin(math.radians(obl)) * math.sin(math.radians(l))

    # Calculate the moon's right ascension and declination
    ra = math.atan2(y, x)
    dec = math.asin(z / r)

    # Calculate the moon's phase angle
    lst = (100.46 + 0.985647352 * jd + longitude) % 360
    ha = (lst - ra) % 360
    phase_angle = math.degrees(math.acos(math.sin(math.radians(latitude)) * math.sin(math.radians(dec)) + math.cos(math.radians(latitude)) * math.cos(math.radians(dec)) * math.cos(math.radians(ha))))

    # Determine the phase of the moon
    # if phase_angle < 90:
    #     return "Waxing Crescent"
    # elif phase_angle < 180:
    #     return "First Quarter"
    # elif phase_angle < 270:
    #     return "Waxing Gibbous"
    # else:
    #     return "Full Moon"

    return phase_angle
