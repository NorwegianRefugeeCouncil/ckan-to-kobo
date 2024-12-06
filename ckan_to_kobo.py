"""
File to push CKAN countries list into Kobo
"""

import json
import click
from kobo.utils import KoboAPI
from ndx.utils import get_csv_resource_as_json


@click.command()
@click.option('--dataset-url', help='URL to a CSV resource in a CKAN/NDX dataset', type=str, required=True)
@click.option('--key-field', help='CSV field to be used as key. e.g. ISO3', type=str, required=True)
@click.option('--value-field', help='CSV field to be used as value. e.g. "Countries and Territories"', type=str, required=True)
@click.option('--use-cache', is_flag=True, help='Cache and reuse NDX base data')
@click.option('--question-label', help='Label for the question block', type=str, required=True)
@click.option(
    '--kobo-collection-id', type=str,
    help='Kobo collection ID, use here or in config.json'
)
@click.option(
    '--kobo-question-block-id', type=str,
    help='Kobo question block ID. Leave empty to create new, use here or in config.json to update'
)
def main(
    dataset_url, key_field, value_field, use_cache,
    question_label, kobo_collection_id=None, kobo_question_block_id=None
):
    """ Command to create or update a question block in a Kobo collection """

    # Validate the config values
    config = get_config()
    if 'ckan_api_token' not in config:
        raise ValueError('ckan_api_token is required in config.json')
    ndx_api_token = config['ndx_api_token']
    if 'kobo_api_token' not in config:
        raise ValueError('kobo_api_token is required in config.json')
    if 'kobo_base_url' not in config:
        raise ValueError('kobo_base_url is required in config.json')
    if kobo_collection_id is None:
        # Check the config.json file, this required
        kobo_collection_id = config.get('kobo_collection_id')
        if kobo_collection_id is None:
            raise ValueError('kobo_collection_id is required')
    if kobo_question_block_id is None:
        # Check the config.json file, this is not required
        kobo_question_block_id = config.get('kobo_question_block_id')
        # If the user did not provide a question block ID, we will create a new one
        # Ask the user to ensure:
        if kobo_question_block_id is not None:
            click.secho(
                f'Using question block ID {kobo_question_block_id}',
                fg='yellow'
            )
            click.confirm('Are you sure you want to use this question block ID?', abort=True)
        else:
            click.secho(
                'No question block ID provided, a new question block will be created',
                fg='yellow'
            )
            click.confirm('Are you sure you want to create a new question block?', abort=True)

    init_display_params = (
        f'Params:\n\tdataset_url={dataset_url} '
        f'key_field={key_field}\n\t'
        f'value_field={value_field}\n\t'
        f'use_cache={use_cache}\n\t'
        f'kobo_collection_id={kobo_collection_id}\n\t'
        f'kobo_question_block_id={kobo_question_block_id}'
    )
    click.secho(init_display_params, fg='blue')

    # Get the data to move to Kobo
    # bg='blue', fg='white', blink=True, bold=True
    click.secho('Getting data from CKAN', fg='green', bold=True)

    data_map = get_csv_resource_as_json(dataset_url, ckan_api_token, key_field, value_field, use_cache)
    total_records = len(data_map)

    click.secho(f'{total_records} records found')
    if total_records == 0:
        click.secho(f'No records found {data_map}', fg='red', bold=True)
        return
    c = 0
    for key, value in data_map.items():
        if c < 10 or c > total_records - 10:
            click.secho(f' - {key}: {value}')
        elif c == 10:
            click.secho('...')
        c += 1

    click.secho('Connecting to Kobo', fg='green', bold=True)
    kobo = KoboAPI(config['kobo_base_url'], config['kobo_api_token'])
    # Analyze currect collection in Kobo
    kobo_collection = kobo.get_collection(config['kobo_collection_id'])
    click.secho('Kobo collection found', fg='green', bold=True)
    click.secho(f' - Owner @{kobo_collection["owner__username"]}')
    choices = [
        {'label': label, 'name': code}
        for code, label in data_map.items()
    ]
    # Create a question block for the countries
    if not kobo_question_block_id:
        question_block = kobo.create_question_block(
            kobo_collection_id=kobo_collection_id,
            question_label=question_label,
            choices=choices,
        )
        question_block_uid = question_block['uid']
        click.secho(f'Question block created: ID:{question_block_uid}', fg='green', bold=True)
    else:
        question_block = kobo.update_question_block(
            kobo_question_block_id,
            question_label=question_label,
            choices=choices,
        )
        click.secho(f'Question block updated', fg='green', bold=True)


def get_config():
    """
    Get config from config.json file
    To be filled with the following structure:
    {
        "ckan_countries_dataset_url": "",
        "ckan_api_token": "",
        "kobo_base_url": "",
        "kobo_api_token": "",
        "kobo_collection_id": ""
    }
    """
    config = json.load(open('config.json'))
    return config


if __name__ == '__main__':
    main()
