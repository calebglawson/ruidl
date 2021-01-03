'''
This file contains the necessary components to mass-unblock / mass-unmute users.
'''

import os
import json
from glob import glob

import requests
import praw
import typer
import hashlib


APP = typer.Typer()


def _make_config():
    '''
    Load the config from a file.
    '''
    config = open('./config.json')
    return json.load(config)


def _make_api(config):
    '''
    Make a PRAW api object.
    '''

    api = praw.Reddit(
        client_id=config.get('client_id'),
        client_secret=config.get('client_secret'),
        user_agent='script:com.example.ruidl:v1 (by u/)',
        username=config.get('username'),
        password=config.get('password')
    )

    return api


def _existing_orig_filenames(base_path):
    raw = glob(f'{base_path}/*.jpg')
    return [fn.split('_')[1] for fn in raw]


def _existing_checksums(base_path):
    raw = glob(f'{base_path}/*.jpg')
    return [fn.split('_')[0].replace(f'{base_path}\\', '') for fn in raw]


def _process_submission(submission, base_path):
    if 'jpg' in submission.url:
        if not os.path.exists(base_path):
            os.makedirs(base_path)

        file_name = f'{base_path}/{submission.url.split("/")[-1]}'
        if file_name not in _existing_orig_filenames(base_path):
            request = requests.get(submission.url)
            file_hash = hashlib.md5(request.content).hexdigest()
            if file_hash not in _existing_checksums(base_path):
                new_file_name = f'{base_path}/{file_hash}_{file_name.split("/")[-1]}'

                with open(new_file_name, 'wb') as new:
                    new.write(request.content)


@APP.command()
def user(name: str, limit: int = typer.Option(None)):
    '''
    Download pictures from the specified user.
    '''
    api = _make_api(_make_config())
    red = api.redditor(name)
    base_path = f'./{name.replace("_", "-")}'

    raw_submissions = red.submissions.new(limit=limit)

    with typer.progressbar(raw_submissions, length=limit) as submissions:
        for submission in submissions:
            _process_submission(submission, base_path)


@APP.command()
def subreddit(
        name: str,
        search: str = typer.Option(None),
        limit: int = typer.Option(500)
):
    '''
    Download pictures from the specified subreddit.
    '''
    api = _make_api(_make_config())
    red = api.subreddit(name)
    base_path = f'./{name.replace("_", "-")}'

    raw_submissions = red.search(
        search,
        sort='new',
        limit=limit
    ) if search else red.new(
        limit=limit
    )
    with typer.progressbar(raw_submissions, length=limit) as submissions:
        for submission in submissions:
            _process_submission(submission, base_path)


if __name__ == '__main__':
    APP()
