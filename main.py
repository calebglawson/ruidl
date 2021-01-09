'''
This file contains the necessary components to download images from a subbreddit or redditor.
'''

import os
import json
import hashlib
from glob import glob

import requests
import praw
import typer


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


def _base_path(name):
    return f'./{name.replace("_", "-")}'


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
def redditor(name: str, limit: int = typer.Option(None)):
    '''
    Download pictures from the specified user.
    '''
    redditor = _make_api(_make_config()).redditor(name)
    raw_submissions = redditor.submissions.new(limit=limit)

    with typer.progressbar(raw_submissions, length=limit) as submissions:
        for submission in submissions:
            _process_submission(submission, _base_path(name))


@APP.command()
def subreddit(
        name: str,
        search: str = typer.Option(None),
        limit: int = typer.Option(500)
):
    '''
    Download pictures from the specified subreddit.
    '''
    sub_reddit = _make_api(_make_config()).subreddit(name)

    raw_submissions = sub_reddit.search(
        search,
        sort='new',
        limit=limit
    ) if search else sub_reddit.new(
        limit=limit
    )
    with typer.progressbar(raw_submissions, length=limit) as submissions:
        for submission in submissions:
            _process_submission(submission, _base_path(name))


if __name__ == '__main__':
    APP()
