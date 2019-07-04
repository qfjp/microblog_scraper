import sys
from secrets import (TWITTER_APP_KEY, TWITTER_APP_SECRET, TWITTER_KEY,
                     TWITTER_SECRET)

import dill
import tweepy


def authenticate_twitter():
    auth = tweepy.OAuthHandler(TWITTER_APP_KEY, TWITTER_APP_SECRET)
    auth.set_access_token(TWITTER_KEY, TWITTER_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    return api


def reload_object(fname, default_obj):
    result = None
    try:
        with open(fname, "rb") as pickle_file:
            result = dill.load(pickle_file)
    except FileNotFoundError:
        print(f"Existing db not found at {fname}, reinitializing...")
        result = default_obj()
    return result


def pickle_it(picklable, fname):
    try:
        with open(fname, "wb") as pickle_file:
            dill.dump(picklable, pickle_file)
    except FileNotFoundError:
        sys.stderr.write(f"ERROR: {fname} is not writeable!\n")
        return False
    return True
