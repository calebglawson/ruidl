# ruidl
Reddit Media Downloader

1. Obtain a client ID and secret from Reddit by [creating a script type app](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example).
2. Create a `config.json` containing the `client_id` and `client_secret`. `username` and `password` are optional and are only needed if you are not receiving the results you expect.
```json
{
    "client_id": "******************",
    "client_secret": "**************",
    "username": "***********optional",
    "password": "***********optional",
    "download_dir": "*******optional",
    "file_size_threshold": "optional",
}
```
3. Download media from a user.
```
python main.py redditor ImAnExampleUser --limit 50
```
Download media from a subreddit.
```
python main.py subreddit imanexamplesubreddit --search "some search terms" --limit 50
```