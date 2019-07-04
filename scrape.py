import sys
from secrets import KEYWORDS

import tweepy

from global_vars import (FILE_NOT_FOUND_EXIT_CODE, NUM_TWEETS_TO_GRAB,
                         TWEETS_FNAME, USERS_FNAME)
from utils import authenticate_twitter, pickle_it, reload_object

NEW_TWEETS = 0
NEW_USERS = 0

TWEET_DICT = reload_object(TWEETS_FNAME, dict)
USER_DICT = reload_object(USERS_FNAME, dict)


class StreamListener(tweepy.StreamListener):
    def on_status(self, tweet):
        global NEW_TWEETS
        global NEW_USERS

        user_id = tweet.user.id_str
        tweet_json = tweet._json

        if user_id not in TWEET_DICT:
            NEW_USERS += 1

        init_len = 0
        try:
            init_len = len(TWEET_DICT[user_id])
            TWEET_DICT[user_id].append(tweet_json)
        except KeyError:
            TWEET_DICT[user_id] = [tweet_json]

        if user_id not in USER_DICT:
            USER_DICT[user_id] = tweet.user._json
            USER_DICT[user_id]["followers"] = []
            USER_DICT[user_id]["friends"] = []

        # update tweet num
        after_len = len(TWEET_DICT[user_id])
        if init_len < after_len:
            NEW_TWEETS += 1

        if NEW_TWEETS >= NUM_TWEETS_TO_GRAB:
            if not pickle_it(TWEET_DICT, TWEETS_FNAME):
                sys.stderr.write(f"ERROR: Failed final pickling, abort!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            if not pickle_it(USER_DICT, USERS_FNAME):
                sys.stderr.write(f"ERROR: Failed final pickling, abort!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            return False

        if NEW_TWEETS % 100 == 0:
            print(f"currently scraped {NEW_TWEETS} new tweets")
            if not pickle_it(TWEET_DICT, TWEETS_FNAME):
                sys.stderr.write(f"failed to pickle after {NEW_TWEETS} tweets")
            if not pickle_it(USER_DICT, USERS_FNAME):
                sys.stderr.write(f"failed to pickle after {NEW_TWEETS} tweets")

    def on_error(self, status_code):
        if status_code == 420:
            # Rate Limited
            return False


def main():
    api = authenticate_twitter()

    stream = tweepy.Stream(auth=api.auth, listener=stream_listener)
    stream.filter(track=KEYWORDS)
    stream_listener = StreamListener()


if __name__ == "__main__":
    main()
