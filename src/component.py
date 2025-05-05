"""
OpenTable API Extractor Component main class.
"""
import logging
from datetime import datetime, UTC

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

from configuration import Configuration
from api_client import APIClient
from utils import write_output_table_if_data


class Component(ComponentBase):
    def __init__(self):
        super().__init__()

    def run(self):
        run_time = datetime.now(UTC)
        run_time_str = run_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        config = Configuration(**self.configuration.parameters)
        state = self.get_state_file()
        api_client = APIClient(config, state)
        new_state = {}

        def sync(name: str, records, primary_key: list[str]):
            return write_output_table_if_data(
                self,
                name=name,
                records=records,
                primary_key=primary_key,
                incremental=(config.sync_options.sync_mode == "incremental_sync")
            )

        if config.endpoints.reservations:
            logging.info("Fetching reservations...")
            sync("reservations", api_client.get_reservations(), primary_key=["reservation_id"])

        if config.endpoints.guests:
            logging.info("Fetching guests...")
            sync("guests", api_client.get_guests(), primary_key=["guest_id"])

        if config.endpoints.directory:
            logging.info("Fetching directory...")
            sync("directory", api_client.get_directory(), primary_key=["id"])

        if config.endpoints.crm_loyalty:
            logging.info("Fetching CRM loyalty data...")
            sync("crm_loyalty", api_client.get_crm_loyalty(), primary_key=["member_id"])

        if config.endpoints.crm_guest_insights:
            logging.info("Fetching CRM guest insights...")
            sync("crm_guest_insights", api_client.get_crm_guest_insights(), primary_key=["guest_id"])

        if config.endpoints.property_details:
            logging.warning("Skipping property_details: per-ID logic must be implemented manually.")

        new_state["last_successful_run"] = run_time_str
        self.write_state_file(new_state)
        logging.info("Data extraction completed.")


if __name__ == "__main__":
    try:
        Component().execute_action()
    except UserException as e:
        logging.exception(e)
        exit(1)
    except Exception as e:
        logging.exception(e)
        exit(2)
