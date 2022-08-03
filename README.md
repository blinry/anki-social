Social features for Anki!

## Setup

On Android, install [Termux](https://f-droid.org/en/packages/com.termux/), and `pkg install python`.

On all platforms:

```
pip install appdirs
```

If you want to post new achievements on Mastodon, go to `Settings -> Development` in your Mastodon web client, add a new application (called "anki-social", for example), click on it, and put your "access token" and your Mastodon instance URL into the file `.env`, like this:

```
ACCESS_TOKEN=<your_access_token_here>
API_BASE_URL=https://your.cool.mastodon.social
```

You will be asked each time before this script sends a toot.

## Usage

```
python anki-social.py
```
