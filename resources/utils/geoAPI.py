from __future__ import division
import math

import typing
from dataclasses import dataclass

from ..core import ClSession

import config

_URL = 'https://nominatim.openstreetmap.org'
_HEADERS = {"User-Agent": config.GEO_API_USER_AGENT}

GeoPointType = typing.Tuple[float, float]  # coordinates lan/lon
LocationType = typing.Union[GeoPointType, str]  # geopoint or city name


@dataclass(eq=False, frozen=True)
class GeoData:
    coordinates: GeoPointType
    city: str
    state: str
    country: str


class _GeoAPI:

    async def get_geo_data(self, locality: LocationType, lang: str = 'ru') -> GeoData:
        client = await ClSession.get_instance()
        if isinstance(locality, str):
            data = {"city": locality}
            route = "/search"
        else:
            data = {'lan': locality[0], "lon": locality[1]}
            route = '/reverse'

        data.update({'addressdetails': 1, "accept-language": lang, "format": "jsonv2"})
        async with client.get(_URL + route, params=data, headers=_HEADERS) as resp:
            assert resp.status == 200
            json_response = (await resp.json())[0]

        address = json_response['address']

        city = ''
        if not address.get('city'):
            if not address.get('town'):
                if not address.get("administrative"):
                    if not address.get('city_district'):
                        if not address.get('county'):
                            if not address.get('state'):
                                city = address['state']
                        else:
                            city = address['county']
                    else:
                        city = address['city_district']
                else:
                    city = address['administrative']
            else:
                city = address['town']
        else:
            city = address['city']
        if not address.get('state'):
            address['state'] = city

        return GeoData(
            (float(json_response['lat']), float(json_response['lon'])),
            city,
            address['state'],
            address['country']
        )

    @staticmethod
    def calculate_distance(local_1: GeoPointType, local_2: GeoPointType, max_iter=55, tol=10 ** -12) -> float:
        if local_1 ==local_2:
            return 0.0
        """
        Nathan A. Rooy
        2016-SEP-30
        Solve the inverse Vincenty's formulae
        https://en.wikipedia.org/wiki/Vincenty%27s_formulae
        :param local_1:
        :param local_2:
        :param max_iter:
        :param tol:
        :return:
        """

        a = 6378137.0  # radius at equator in meters (WGS-84)
        f = 1 / 298.257223563  # flattening of the ellipsoid (WGS-84)
        b = (1 - f) * a

        phi_1, l_1, = local_1
        phi_2, l_2, = local_2

        u_1 = math.atan((1 - f) * math.tan(math.radians(phi_1)))
        u_2 = math.atan((1 - f) * math.tan(math.radians(phi_2)))

        l_ = math.radians(l_2 - l_1)

        lambda_ = l_  # set initial value of lambda to L

        sin_u1 = math.sin(u_1)
        cos_u1 = math.cos(u_1)
        sin_u2 = math.sin(u_2)
        cos_u2 = math.cos(u_2)

        # --- BEGIN ITERATIONS -----------------------------+
        iter_count: int = 0
        cos_sq_alpha: float = 0.0
        cos2_sigma_m: float = 0.0
        sigma: float = 0
        cos_sigma: float = 0
        sin_sigma: float = 0
        for i in range(0, max_iter):
            iter_count += 1
            cos_lambda = math.cos(lambda_)
            sin_lambda = math.sin(lambda_)
            sin_sigma = math.sqrt((cos_u2 * math.sin(lambda_)) ** 2 + (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda) ** 2)
            cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lambda
            sigma = math.atan2(sin_sigma, cos_sigma)
            sin_alpha = (cos_u1 * cos_u2 * sin_lambda) / sin_sigma
            cos_sq_alpha = 1 - sin_alpha ** 2
            cos2_sigma_m = cos_sigma - ((2 * sin_u1 * sin_u2) / cos_sq_alpha)
            c_ = (f / 16) * cos_sq_alpha * (4 + f * (4 - 3 * cos_sq_alpha))
            lambda_prev = lambda_
            lambda_ = l_ + (1 - c_) * f * sin_alpha * (
                        sigma + c_ * sin_sigma * (cos2_sigma_m + c_ * cos_sigma * (-1 + 2 * cos2_sigma_m ** 2)))

            # successful convergence
            diff = abs(lambda_prev - lambda_)
            if diff <= tol:
                break

        u_sq = cos_sq_alpha * ((a ** 2 - b ** 2) / b ** 2)
        a_ = 1 + (u_sq / 16384) * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
        b_ = (u_sq / 1024) * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
        delta_sig = b_ * sin_sigma * (cos2_sigma_m + 0.25 * b_ * (
                    cos_sigma * (-1 + 2 * cos2_sigma_m ** 2) - (1 / 6) * b_ * cos2_sigma_m * (
                        -3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos2_sigma_m ** 2)))

        m = b * a_ * (sigma - delta_sig)  # output distance in meters
        return m
