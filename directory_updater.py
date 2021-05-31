'''
This file is intended for a sequential bulk update of either Redditors or Subreddits
contained within a directory consisting of a single type.
'''

from glob import glob
from pathlib import Path
from os import listdir
import typer

from ruidl import Redditor, Subreddit

APP = typer.Typer()


def _update(
    kind,
    kind_path,
    download_directory,
    limit,
    verbose,
    search=None
):
    dl_dir = Path(download_directory, kind_path)
    typer.echo(dl_dir)

    directories = [
        item for item in listdir(
            dl_dir
        ) if Path(f'{dl_dir}/{item}').is_dir()
    ]

    for name in directories:
        # Windows Folder Names are allergic to underscores, they had to be escaped.
        crumbs = glob(f'{download_directory}/{kind_path}/{name}/*.crumb')
        if crumbs:
            name = Path(crumbs[0]).stem

        try:
            typer.echo(f'\n{name}')
            kind(name, download_directory, verbose).get(limit, search)
        except Exception:  # pylint: disable=broad-except
            typer.echo(
                f'Could not retrieve submissions for {name}'
            )


@APP.command()
def redditor(
        download_directory: str,
        limit: int = typer.Option(None),
        verbose: bool = typer.Option(False),
):
    '''
    Download from the specified redditors.
    '''
    _update(
        Redditor,
        'redditor',
        download_directory,
        limit,
        verbose,
        search=None
    )


@APP.command()
def subreddit(
        download_directory: str,
        limit: int = typer.Option(None),
        search: str = typer.Option(None),
        verbose: bool = typer.Option(False),
):
    '''
    Download from the specified subreddits.
    '''
    _update(
        Subreddit,
        'subreddit',
        download_directory,
        limit,
        verbose,
        search
    )


if __name__ == '__main__':
    APP()
