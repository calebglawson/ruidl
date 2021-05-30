'''
This file contains the necessary components to download images from a subbreddit or redditor.
'''

from abc import abstractmethod
import os
import re
import json
import hashlib

import sys
import time
import traceback
from glob import glob
from pathlib import Path
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool

import exif
import requests
import praw
import prawcore
import typer
import wordninja
from bs4 import BeautifulSoup

APP = typer.Typer()

USER_AGENT_HEADER = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0'
    )
}


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


def _ninjify(url):
    words = wordninja.split(url.split("/")[-1])

    capitalized_words = ''
    for idx, word in enumerate(words):
        if idx < 3:
            capitalized_words = f'{capitalized_words}{word[0].upper()}{word[1:]}'
        else:
            capitalized_words = f'{capitalized_words}{word}'

    return capitalized_words


class Ruidl(object):
    '''
    Reddit media downloader.
    '''

    def __init__(self, name, download_directory, verbose):
        self._name = name
        self._verbose = verbose

        self._config = _make_config()
        self._api = _make_api(self._config)
        dl_dir = f'{download_directory}/' if download_directory else self._config.get(
            "download_dir", "./"
        )
        self._base_path = f'{dl_dir}{self._name.replace("_", "-")}'

        if not os.path.exists(self._base_path):
            os.makedirs(self._base_path)

        self._filetypes = [
            '.jpg',
            '.png',
            '.gif',
            '.mp4',
            '.webm'
        ]
        existing_files = []
        for file_type in self._filetypes:
            existing_files.extend(glob(f'{self._base_path}/*{file_type}'))
        self._filenames = {fn.split('_')[1] for fn in existing_files}
        self._checksums = {
            fn.split('_')[0].replace(f'{self._base_path}\\', '') for fn in existing_files
        }
        del existing_files

        wordninja.DEFAULT_LANGUAGE_MODEL = wordninja.LanguageModel(
            Path('./wordninja_words.txt.gz')
        )

    def _download_file(self, file_url, submission):
        file_name = f'{self._base_path}/{file_url.split("/")[-1]}'

        if file_name in self._filenames:
            return

        request = requests.get(file_url, headers=USER_AGENT_HEADER)
        file_hash = hashlib.md5(request.content).hexdigest()
        if file_hash in self._checksums:
            return

        self._checksums.add(file_hash)
        self._filenames.add(file_name.split("/")[-1].split("?")[0])
        new_file_name = f'{self._base_path}/{file_hash}_{file_name.split("/")[-1].split("?")[0]}'

        if sys.getsizeof(request.content) < self._config.get('file_size_threshold', 10000):
            return

        with open(new_file_name, 'wb') as new:
            new.write(request.content)

        if any([file_type in file_name for file_type in ['mp4', 'gif', 'png', 'webm']]):
            return

        try:
            with open(new_file_name, 'rb') as new:
                image = exif.Image(new.read())
                image.artist = str(submission.author)
                image.image_description = str(submission.subreddit)

            with open(new_file_name, 'wb') as new:
                new.write(image.get_file())
        except Exception as exception:  # pylint: disable=broad-except
            if self._verbose:
                typer.echo(
                    f'Error writing Exif data: {new_file_name} {exception}'
                )

    def _get_file_urls(self, submission):
        file_urls = []
        if any([ext in submission.url for ext in self._filetypes]):
            file_urls = [submission.url]
        elif 'reddit.com/gallery' in submission.url:
            request = requests.get(
                submission.url,
                headers=USER_AGENT_HEADER
            )
            soup = BeautifulSoup(request.content, features='html.parser')
            file_urls = [
                elem.get('href')
                for elem in
                soup.find_all(
                    'a',
                    href=re.compile('preview.redd.it'),
                    attrs={'target': '_blank'}
                )
            ]
        elif 'imgur.com/a/' in submission.url:
            # Imgur gallery, multiple images.
            gallery = submission.url.split("/")[-1]
            request = requests.get(
                f'https://imgur.com/ajaxalbums/getimages/{gallery}',
                headers=USER_AGENT_HEADER
            )
            response = json.loads(request.content)
            file_urls = [
                f'https://i.imgur.com/{image["hash"]}{image["ext"]}'
                for image in
                response['data']['images']
            ]
        elif 'imgur.com/' in submission.url:
            # Single imgur image.
            image = submission.url.split("/")[-1]
            file_urls = [f'https://i.imgur.com/{image}.jpg']
        elif (
                self._config.get('wordninja_trigger') and
                self._config.get('wordninja_trigger') in submission.url
        ):
            file_urls = [
                (
                    f'{self._config.get("wordninja_download_url","")}'
                    f'{_ninjify(submission.url)}.mp4'
                )
            ]
        elif 'gfycat.com/' in submission.url:
            file_urls = [
                f'https://giant.gfycat.com/{_ninjify(submission.url)}.webm'
            ]
        else:
            if self._verbose:
                typer.echo(
                    f'No match triggered for this URL: {submission.url} '
                    f'Permalink: https://reddit.com{submission.permalink}'
                )

        return file_urls

    def _process_submission(self, submission):
        try:
            file_urls = self._get_file_urls(submission)

            for file_url in file_urls:
                self._download_file(file_url, submission)

        except Exception as exception:  # pylint: disable=broad-except
            # Needed so that any exceptions in threads are loud and clear.
            if self._verbose:
                typer.echo(exception)
                typer.echo(traceback.format_exc())

    def _handle_submissions(self, submissions):
        num_threads = cpu_count() if len(submissions) > cpu_count() else len(submissions)

        if num_threads:
            if any(character in self._name for character in ['-', '_']):
                # We only place crumbs when they're needed.
                Path(f'{self._base_path}/{self._name}.crumb').touch()

            typer.echo(
                f'Processing {len(submissions)} submissions with {num_threads} worker thread(s).'
            )

            thread_pool = ThreadPool(num_threads)

            start_file_num = len(os.listdir(self._base_path))
            start = time.time()
            thread_pool.map_async(self._process_submission, submissions)
            thread_pool.close()
            thread_pool.join()
            end = time.time()
            end_file_num = len(os.listdir(self._base_path))

            typer.echo(
                f'Downloaded {end_file_num - start_file_num} '
                f'files within {int(end - start)} seconds.'
            )
        else:
            typer.echo(f'No submissions found, nothing to process.')

        self._clean_empty_dir()

    def _clean_empty_dir(self):
        if len(os.listdir(self._base_path)) == 0:
            os.rmdir(self._base_path)

    @abstractmethod
    def get(self, limit, search):
        '''
        Process the request to Reddit.
        '''
        raise NotImplementedError


class Redditor(Ruidl):
    '''
    A Redditor is a Reddit User.
    '''

    def get(self, limit, search):
        '''
        Download content
        '''
        try:
            redd = self._api.redditor(self._name)
            typer.echo('Retrieving submission list.')
            submissions = [
                submission for submission in redd.submissions.new(limit=limit)
            ]

            self._handle_submissions(submissions)
        except prawcore.exceptions.NotFound:
            typer.echo(f'Could not find redditor {self._name}.')
            self._clean_empty_dir()


class Subreddit(Ruidl):
    '''
    A Subreddit is a community page on Reddit.
    '''

    def get(self, limit, search):
        '''
        Download content
        '''
        try:
            sub = self._api.subreddit(self._name)
            typer.echo('Retrieving submission list.')
            submissions = [
                submission for submission in
                (
                    sub.search(
                        search,
                        sort='new',
                        limit=limit
                    ) if search else sub.new(
                        limit=limit
                    )
                )
            ]
            self._handle_submissions(submissions)
        except prawcore.exceptions.Redirect:
            typer.echo(f'Could not find subreddit {self._name}.')
            self._clean_empty_dir()


@APP.command()
def redditor(
        name: str,
        limit: int = typer.Option(None),
        download_directory: str = typer.Option(None),
        verbose: bool = typer.Option(False),
):
    '''
    Download from the specified user.
    '''
    Redditor(name, download_directory, verbose).get(limit, search=None)


@APP.command()
def subreddit(
        name: str,
        limit: int = typer.Option(None),
        search: str = typer.Option(None),
        download_directory: str = typer.Option(None),
        verbose: bool = typer.Option(False),
):
    '''
    Download from the specified subreddit.
    '''
    Subreddit(name, download_directory, verbose).get(limit, search)


if __name__ == '__main__':
    APP()
