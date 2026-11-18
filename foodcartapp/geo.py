import logging
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    try:
        response = requests.get(base_url, params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        }, timeout=5)
        response.raise_for_status()
        found_places = response.json()['response']['GeoObjectCollection']['featureMember']
    except RequestException as e:
        logger.warning(f"Геокодер: сетевая ошибка для «{address}»: {e}")
        return None
    except (ValueError, KeyError, TypeError) as e:
        logger.warning(f"Геокодер: ошибка в данных ответа для «{address}»: {e}")
        return None

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon
