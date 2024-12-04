import csv
import logging
import sys

from io import StringIO
from pathlib import Path

import requests


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)
SAMPLE_DATA_FOLDER = 'sample-data'


def get_csv_resource_as_json(
    ckan_dataset_url,
    ckan_api_token,
    key_field,
    value_field,
    use_cache=False
):
    """ Get CKAN resource data
        Params:
         - ckan_dataset_url: URL to the CKAN dataset
         - ckan_api_token: CKAN API token
         - key_field: field name to use as key (e.g. 'ISO3' for the countries dataset)
         - value_field: field name to use as value (e.g. 'Countries and Territories' for the countries dataset)

        Returns a dictionary using key and values from CSV fields

    """
    log.info(f'Getting CKAN dataset from URL {ckan_dataset_url}')
    file_name = ckan_dataset_url.split('/')[-1]
    csv_data = None
    # SAMPLE_DATA_FOLDER + file_name
    cache_file = Path(SAMPLE_DATA_FOLDER) / file_name
    if use_cache:
        # Check if we have a cached version of the data
        if cache_file.exists():
            print('Using cached data')
            csv_data = open('cached.csv')

    if not csv_data:
        headers = {
            'Authorization': ckan_api_token,
        }
        response = requests.request("GET", ckan_dataset_url, headers=headers)
        # Transform this to JSON replacing field names from
        # "Countries and Territories" to "country" and "ISO3" to "code"
        csv_data = StringIO(response.text)
        # Save for next time
        # create the file if not exists
        cache_file.touch(exist_ok=True)
        cache_file.write_text(response.text)

    csv_data_str = csv_data.getvalue()
    log.info(f'\n **** CSV data **** \n\n{csv_data_str[:100]}...\n')
    data = csv.DictReader(csv_data)
    ret_data = {}

    try:
        for row in data:
            ret_data[row[key_field]] = row[value_field]
    except KeyError as e:
        log.error(
            f'Expected: Key field: {key_field} - Value field: {value_field}'
            f'Error: {e} in row\n\t{row}'
            f'response status: {response.status_code}'
        )
        raise e
    return ret_data
