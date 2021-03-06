'''
Test suite for Ruidl.
'''

from collections import namedtuple
from pytest import mark

from ruidl import Redditor

Submission = namedtuple('Submission', ['url', "permalink"])


@mark.parametrize("submission, expected_urls", [
    # Empty, usually exits before this point
    (Submission(url="", permalink=""), []),
    # Any direct image link
    (
        Submission(
            url="i.reddit.com/image.jpg",
            permalink=""
        ),
        ["i.reddit.com/image.jpg"]
    ),
    # Gfycat
    (
        Submission(
            url="gfycat.com/purplechickenmonkey",
            permalink=""
        ),
        ["https://giant.gfycat.com/PurpleChickenMonkey.webm"]
    )
])
def test_get_file_urls(submission, expected_urls):
    '''
    Testing URL extraction from Reddit submissions.
    '''

    redditor = Redditor(name="test", download_directory="", verbose=True)

    result = redditor._get_file_urls(  # pylint: disable=protected-access
        submission
    )

    assert result == expected_urls
