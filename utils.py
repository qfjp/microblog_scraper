import gzip
import random
import sys
from secrets import TWITTER_APP_KEY, TWITTER_APP_SECRET, TWITTER_KEY, TWITTER_SECRET

import dill
import tweepy

import ujson
from global_vars import USER_DICT_FNAME, USER_LIST_FNAME


def authenticate_twitter():
    auth = tweepy.OAuthHandler(TWITTER_APP_KEY, TWITTER_APP_SECRET)
    auth.set_access_token(TWITTER_KEY, TWITTER_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    return api


def reload_object(fname_base, default_obj):
    fname = fname_base + ".pkl.gz"
    result = None
    try:
        with gzip.open(fname, "rb") as pickle_file:
            result = dill.load(pickle_file)
    except FileNotFoundError:
        print(f"Existing db not found at {fname}, reinitializing...")
        result = default_obj()
    return result


def reload_json(fname_base, default_obj, transform=None):
    fname = fname_base + ".json.gz"
    if transform is None:
        transform = lambda x: x
    result = None
    try:
        with gzip.open(fname, "rt") as json_file:
            result = transform(ujson.load(json_file))
    except FileNotFoundError:
        sys.stderr(f"Existing object not found at {fname}, reinitializing")
    return result


def json_it(jsonable, fname_base, transform=None):
    fname = fname_base + ".json.gz"
    if transform is None:
        transform = lambda x: x
    print(f"Dumping object as json to {fname}")
    json = transform(jsonable)
    try:
        with gzip.open(fname, "wt") as json_file:
            ujson.dump(json, json_file)
    except FileNotFoundError:
        sys.stederr.write(f"ERROR: {fname} is not writeable!\n")
        return False
    return True


def pickle_it(picklable, fname_base):
    fname = fname_base + ".pkl.gz"
    print(f"Pickling object to {fname}")
    try:
        with gzip.open(fname, "wb") as pickle_file:
            dill.dump(picklable, pickle_file)
    except FileNotFoundError:
        sys.stderr.write(f"ERROR: {fname} is not writeable!\n")
        return False
    return True


def compile_users_n_others(reset=False):
    if not reset:
        return reload_object(USER_LIST_FNAME, set)
    users = {}
    user_dict = reload_object(USER_DICT_FNAME, dict)
    for user in user_dict:
        this_user_set = set()
        for follower in user_dict[user]["followers"]:
            this_user_set.add(str(follower))
        for friend in user_dict[user]["friends"]:
            this_user_set.add(str(friend))
        users[user] = this_user_set
    pickle_it(users, USER_LIST_FNAME)
    return users
