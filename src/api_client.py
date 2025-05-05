import logging
import requests
from typing import Dict, Generator, Any
from urllib.parse import urljoin

from configuration import Configuration

DEFAULT_PAGE_SIZE = 25


class APIClient:
    def __init__(self, config: Configuration, state: Dict[str, str]):
        self.config = config
        self.state = state
        self.base_url = self.config.authorization.get_base_url()
        self.token = self._authenticate()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    def _authenticate(self) -> str:
        """
        Authenticate using OAuth2 client credentials grant and return access token.
        """
        url = f"{self.base_url}/oauth/token"
        logging.debug(f"Authenticating at {url}")

        try:
            response = requests.post(
                url,
                data={"grant_type": "client_credentials"},
                auth=(self.config.authorization.client_id, self.config.authorization.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token = response.json()["access_token"]
            logging.debug("Authentication successful.")
            return token
        except Exception as e:
            raise RuntimeError(f"Failed to authenticate: {e}")

    def _get_paginated(self, endpoint: str, params: Dict[str, Any] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Generalized pagination handler.
        """
        page = 1
        while True:
            query = params.copy() if params else {}
            query.update({"page": page, "per_page": DEFAULT_PAGE_SIZE})
            url = urljoin(self.base_url, endpoint)
            logging.debug(f"Requesting: {url} | Page: {page}")

            try:
                response = requests.get(url, headers=self.headers, params=query)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logging.warning(f"Request failed on page {page}: {e}")
                break

            records = (
                data.get("data") or
                data.get("reservations") or
                data.get("guests") or
                data.get("restaurants") or
                []
            )

            if not isinstance(records, list) or not records:
                break

            for item in records:
                yield item

            page += 1

    def get_reservations(self) -> Generator[Dict[str, Any], None, None]:
        start = self.config.sync_options.resolved_date_from(self.state).strftime("%Y-%m-%d")
        end = self.config.sync_options.resolved_date_to().strftime("%Y-%m-%d")
        return self._get_paginated("/api/v1/reservations", {"start_date": start, "end_date": end})

    def get_guests(self) -> Generator[Dict[str, Any], None, None]:
        return self._get_paginated("/api/v1/guests")

    def get_directory(self) -> Generator[Dict[str, Any], None, None]:
        return self._get_paginated("/api/v1/restaurants")

    def get_crm_loyalty(self) -> Generator[Dict[str, Any], None, None]:
        return self._get_paginated("/api/v1/crm/loyalty")

    def get_crm_guest_insights(self) -> Generator[Dict[str, Any], None, None]:
        return self._get_paginated("/api/v1/crm/guest-insights")

    def get_property_details(self, property_id: str) -> Dict[str, Any]:
        url = urljoin(self.base_url, f"/api/v1/properties/{property_id}")
        logging.debug(f"Fetching property details from {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Failed to fetch property {property_id}: {e}")
            return {}
