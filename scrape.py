import sys
from secrets import KEYWORDS

import tweepy

from global_vars import (FILE_NOT_FOUND_EXIT_CODE, NUM_TWEETS_TO_GRAB,
                         TWEETS_FNAME, USERS_FNAME)
from utils import authenticate_twitter, pickle_it, reload_object

NEW_TWEETS = 0
NEW_USERS = 0


class StreamListener(tweepy.StreamListener):
    def __init__(self, user_dict, tweet_dict):
        tweepy.StreamListener.__init__(self)
        self.tweet_dict = tweet_dict
        self.user_dict = user_dict

    def on_status(self, tweet):
        global NEW_TWEETS
        global NEW_USERS

        user_id = tweet.user.id_str
        tweet_json = tweet._json

        if user_id not in self.tweet_dict:
            NEW_USERS += 1

        init_len = 0
        try:
            init_len = len(self.tweet_dict[user_id])
            self.tweet_dict[user_id].append(tweet_json)
        except KeyError:
            self.tweet_dict[user_id] = [tweet_json]

        if user_id not in self.user_dict:
            self.user_dict[user_id] = tweet.user._json

        # update tweet num
        after_len = len(self.tweet_dict[user_id])
        if init_len < after_len:
            NEW_TWEETS += 1
        if NEW_TWEETS >= NUM_TWEETS_TO_GRAB:
            if not pickle_it(self.tweet_dict, TWEETS_FNAME):
                sys.stderr.write("ERROR: ABORT!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            if not pickle_it(self.user_dict, USERS_FNAME):
                sys.stderr.write("ERROR: ABORT!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            sys.exit(0)

        if NEW_TWEETS % 100 == 0:
            print(f"currently scraped #{NEW_TWEETS} new tweets")

    def on_error(self, status_code):
        if status_code == 420:
            # Rate Limited
            return False


def main():
    tweet_dict = reload_object(TWEETS_FNAME, dict)
    user_dict = reload_object(USERS_FNAME, dict)
    api = authenticate_twitter()

    stream_listener = StreamListener(user_dict, tweet_dict)
    stream = tweepy.Stream(auth=api.auth, listener=stream_listener)
    stream.filter(track=KEYWORDS)


if __name__ == "__main__":
    main()
