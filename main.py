'''
This file contains the necessary components to download images from a subbreddit or redditor.
'''

import os
import json
import hashlib
import time
from glob import glob
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool

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
        user_agent='script:com.example.ruidl:v1 (by u/anon)',
        username=config.get('username'),
        password=config.get('password')
    )

    return api


class Ruidl:
    '''
    Reddit media downloader.
    '''

    def __init__(self, name):
        self._name = name

        self._config = _make_config()
        self._api = _make_api(self._config)
        self._base_path = f'{self._config.get("download_dir", "./")}{self._name.replace("_", "-")}'

        if not os.path.exists(self._base_path):
            os.makedirs(self._base_path)

        self._filetypes = ['.jpg', '.png', '.gif', '.webp', '.mp4']
        existing_files = []
        for file_type in self._filetypes:
            existing_files.extend(glob(f'{self._base_path}/*{file_type}'))
        self._filenames = {fn.split('_')[1] for fn in existing_files}
        self._checksums = {
            fn.split('_')[0].replace(f'{self._base_path}\\', '') for fn in existing_files
        }
        del existing_files

    def _process_submission(self, submission):
        if any([ext in submission.url for ext in self._filetypes]):

            file_name = f'{self._base_path}/{submission.url.split("/")[-1]}'

            if file_name not in self._filenames:
                request = requests.get(submission.url)
                file_hash = hashlib.md5(request.content).hexdigest()
                if file_hash not in self._checksums:
                    self._checksums.add(file_hash)
                    self._filenames.add(file_name.split("/")[-1])
                    new_file_name = f'{self._base_path}/{file_hash}_{file_name.split("/")[-1]}'
                    with open(new_file_name, 'wb') as new:
                        new.write(request.content)

    def _handle_submissions(self, submissions):
        typer.echo(
            f'Processing submissions with {cpu_count()} worker thread(s).'
        )

        thread_pool = ThreadPool(cpu_count())

        start_file_num = len(os.listdir(self._base_path))
        start = time.time()
        thread_pool.map_async(self._process_submission, submissions)
        thread_pool.close()
        thread_pool.join()
        end = time.time()
        end_file_num = len(os.listdir(self._base_path))

        typer.echo(
            f'Downloaded {end_file_num - start_file_num} files within {int(end - start)} seconds.'
        )

    def redditor(self, limit):
        '''
        Download content from a redditor
        '''
        redd = self._api.redditor(self._name)
        submissions = redd.submissions.new(limit=limit)

        self._handle_submissions(submissions)

    def subreddit(self, search, limit):
        '''
        Download content from a subreddit.
        '''
        sub = self._api.subreddit(self._name)
        submissions = sub.search(
            search,
            sort='new',
            limit=limit
        ) if search else sub.new(
            limit=limit
        )
        self._handle_submissions(submissions)


@APP.command()
def redditor(name: str, limit: int = typer.Option(None)):
    '''
    Download from the specified user.
    '''
    Ruidl(name).redditor(limit)


@APP.command()
def subreddit(
        name: str,
        search: str = typer.Option(None),
        limit: int = typer.Option(500)
):
    '''
    Download from the specified subreddit.
    '''
    Ruidl(name).subreddit(search, limit)


if __name__ == '__main__':
    APP()
