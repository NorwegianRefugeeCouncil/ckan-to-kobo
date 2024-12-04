import json
import logging
import random
import sys
from pathlib import Path

import requests


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)
SAMPLE_DATA_FOLDER = 'sample-data'


class KoboAPI:
    """ Handle Kobo API requests """
    def __init__(self, kobo_base_url, kobo_api_token):
        self.kobo_base_url = kobo_base_url
        self.kobo_api_token = kobo_api_token

    def _build_url(self, url):
        u1 = self.kobo_base_url.rstrip('/')
        u2 = url.lstrip('/')
        final_url = f'{u1}/{u2}'
        return final_url

    def _request(self, url, data={}, method='GET'):
        log.info(f'Requesting Kobo instance from URL {url}::{method}')
        final_url = self._build_url(url)
        headers = {
            'Authorization': f'Token {self.kobo_api_token}',
            'Accept': 'application/json',
        }
        if method.upper() == 'GET':
            response = requests.request("GET", final_url, headers=headers, params=data)
        elif method.upper() == 'POST':
            response = requests.post(final_url, headers=headers, json=data)
        elif method.upper() == 'PUT':
            response = requests.put(final_url, headers=headers, json=data)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(
                f'Error (status={response.status_code}) requesting Kobo instance '
                f'from URL {final_url}: {response.text[:300]}'
            )
            raise e

        # save al request to analyze data and learn how kobo works
        # define a proper file name for this request
        function_who_call_me = sys._getframe(1).f_code.co_name
        file_name = f'{method.lower()}-{function_who_call_me}-{url.replace("/", "-")}.json'
        data_file = Path(SAMPLE_DATA_FOLDER) / file_name
        data_file.touch(exist_ok=True)
        beauty_json = json.dumps(response.json(), indent=4)
        data_file.write_text(beauty_json)

        log.info(f'Request successful to {final_url} = {response.status_code}')
        return response

    def get_asset(self, kobo_asset_id):
        """ Get Kobo collection data """
        log.info(f'Getting Kobo asset {kobo_asset_id}')
        url = f'/api/v2/assets/{kobo_asset_id}/'
        response = self._request(url)
        return response.json()

    def get_collection(self, kobo_collection_id):
        """ A Kobo collection is just an asset """
        log.info(f'Getting Kobo collection {kobo_collection_id}')
        return self.get_asset(kobo_asset_id=kobo_collection_id)

    def get_collection_items(
        self,
        kobo_collection_id,
        item_types=['question', 'block', 'template', 'collection'],
        limit=100,
        offset=0,
    ):
        """
        Get items from a Kobo collection
        See collection-get-items.json
        """
        log.info(f'Getting Kobo collection items for {kobo_collection_id} :: {item_types}')
        url = '/api/v2/assets/'
        asset_types_filter = ' OR '.join([f'asset_type:{item_type}' for item_type in item_types])
        query = f'({asset_types_filter}) AND parent__uid:{kobo_collection_id}'
        response = self._request(
            url,
            data={
                'q': query,
                'limit': limit,
                'offset': offset,
                'ordering': '-date_modified',
                'metadata': 'on',
            }
        )
        return response.json()

    def get_question_blocks(self, kobo_collection_id):
        """ Get just the question blocks """
        log.info(f'Getting Kobo question blocks for {kobo_collection_id}')
        items = self.get_collection_items(kobo_collection_id, item_types=['question'])
        return items

        """
        Add for your own collection, anonymized variables below
        """
  
    def create_new_kobo_collection(
        self,
        collection_name,
        collection_country_code="XXX",
        collection_country_label="XXX",
        collection_sector="XXX",
        collection_description="XXX",
        collection_organization="XXX",
    ):
        """ Create Kobo collection """
        log.info(f'Creating Kobo collection {collection_name}')
        url = '/api/v2/assets/'

        settings = {
            "organization": collection_organization,
            "country": [{"value": collection_country_code, "label": collection_country_label}],
            "sector": {"value": collection_sector, "label": collection_sector},
            "description": collection_description
        }
        data = {
            'name': collection_name,
            'asset_type': 'collection',
            'settings': settings,
            # comma separated list of tags
            'tag_string': '',

        }
        response = self._request(url, data=data, method='POST')
        return response.json()

    def create_question_block(
            self,
            kobo_collection_id,
            question_label, choices, question_type="select_one",
            required=False,
    ):
        """ Create a question block for a Kobo collection
            Choices param must be a list of dictionaries with keys 'label' and 'name'
        """
        log.info(f'Creating question block for Kobo collection {kobo_collection_id}')
        kobo_collection_url = self._build_url(f'/api/v2/assets/{kobo_collection_id}/')
        rand_unique = random.randint(100000, 999999)
        select_from_list_name = f'unique_list_name_{rand_unique}'
        for choice in choices:
            choice['list_name'] = select_from_list_name
        data = {
            'content': {
                "survey": [
                    {
                        "type": question_type,
                        "select_from_list_name": select_from_list_name,
                        "label": question_label,
                        "required": required,
                    },
                ],
                "choices": choices,
                "settings": [{}]
            },
            'asset_type': 'block',
            'parent': kobo_collection_url,
        }
        url = '/api/v2/assets/'
        response = self._request(url, data=data, method='POST')
        return response.json()

    def update_question_block(
            self,
            kobo_question_block_id,
            question_label, choices, question_type="select_one",
            required=False,
    ):
        """ Update a question block for a Kobo collection
            Choices param must be a list of dictionaries with keys 'label' and 'name'
        """
        log.info(f'Updating question block for Kobo collection {kobo_question_block_id}')

        # Get the preious question block to preserve the select_from_list_name
        question_block = self.get_asset(kobo_question_block_id)
        select_from_list_name = question_block['content']['survey'][0]['select_from_list_name']
        # 1 million data but the parent collection ID is in "parent" as last chunck of the URL ...
        kobo_collection_id = question_block['parent'].split('/')[-2]

        url = f'/api/v2/assets/{kobo_question_block_id}/'
        kobo_collection_url = self._build_url(f'/api/v2/assets/{kobo_collection_id}/')
        for choice in choices:
            choice['list_name'] = select_from_list_name
        data = {
            'content': {
                "survey": [
                    {
                        "type": question_type,
                        "select_from_list_name": select_from_list_name,
                        "label": question_label,
                        "required": required,
                    },
                ],
                "choices": choices,
                "settings": [{}]
            },
            'asset_type': 'block',
            'parent': kobo_collection_url,
        }
        response = self._request(url, data=data, method='PUT')
        return response.json()
