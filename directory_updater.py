'''
This file is intended for a sequential bulk update of either Redditors or Subreddits
contained within a directory consisting of a single type.
'''

from glob import glob
from itertools import product
from pathlib import Path
from os import listdir
import typer

from ruidl import Redditor, Subreddit

APP = typer.Typer()


def _name_permutator(name, download_directory):
    '''
    Underscores had to be escaped in folder names,
    so we enumerate the possibilities if we can't find the true name.
    '''

    if '-' not in name:
        # Nothing to do
        return [name]

    crumbs = glob(f'{download_directory}/{name}/*.crumb')
    if crumbs:
        return [Path(crumb).stem for crumb in crumbs]

    permutated_names = []
    permutations = product("-_", repeat=name.count('-'))
    for permutation in permutations:
        permutated_name = []
        occurence = 0
        for character in name:
            if character == '-':
                character = permutation[occurence]
                occurence += 1

            permutated_name.append(character)

        permutated_names.append("".join(permutated_name))

    return permutated_names


def _update(kind, download_directory, limit, verbose, search=None):
    dl_dir = Path(download_directory)
    typer.echo(dl_dir)

    directories = [
        item for item in listdir(
            dl_dir
        ) if Path(f'{dl_dir}/{item}').is_dir()
    ]

    for name in directories:
        for permutated_name in _name_permutator(name, download_directory):
            try:
                typer.echo(f'\n{permutated_name}')
                kind(
                    permutated_name,
                    download_directory,
                    verbose
                ).get(limit, search)
            except Exception:  # pylint: disable=broad-except
                typer.echo(
                    f'Could not retrieve submissions for {permutated_name}'
                )


@APP.command()
def redditors(
        download_directory: str,
        limit: int = typer.Option(None),
        verbose: bool = typer.Option(False),
):
    '''
    Download from the specified redditors.
    '''
    _update(Redditor, download_directory, limit, verbose, search=None)


@APP.command()
def subreddits(
        download_directory: str,
        limit: int = typer.Option(None),
        search: str = typer.Option(None),
        verbose: bool = typer.Option(False),
):
    '''
    Download from the specified subreddits.
    '''
    _update(Subreddit, download_directory, limit, verbose, search)


if __name__ == '__main__':
    APP()
