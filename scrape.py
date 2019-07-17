import datetime as dt
import random

# import signal
import multiprocessing
import sys
from secrets import KEYWORDS

import tweepy
from OpenSSL.SSL import WantReadError
from urllib3.exceptions import ProtocolError

from global_vars import (
    FILE_NOT_FOUND_EXIT_CODE,
    NUM_TWEETS_TO_GRAB,
    TWEETS_FNAME,
    USER_DICT_FNAME,
)
from utils import (
    authenticate_twitter,
    compile_users_n_others,
    reload_object,
    json_it,
    reload_json,
)

GRAB_NEW = False

TWEET_DICT = reload_object(TWEETS_FNAME, dict)
USER_DICT = reload_object(USER_DICT_FNAME, dict)


class StreamListener(tweepy.StreamListener):
    def __init__(self, num_to_grab=NUM_TWEETS_TO_GRAB, api=None, pickle=True):
        super().__init__(api=api)
        self.num_to_grab = num_to_grab
        self.new_tweets = 0
        self.new_users = 0
        self.pickle = pickle

    def keep_alive(self):
        print("keep alive recieved")
        return

    def on_status(self, tweet):
        user_id = tweet.user.id_str
        tweet_json = tweet._json

        if user_id not in TWEET_DICT:
            self.new_users += 1

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
            self.new_tweets += 1

        if self.num_to_grab > 0 and self.new_tweets >= self.num_to_grab:
            if self.pickle and not json_it(TWEET_DICT, TWEETS_FNAME):
                sys.stderr.write(f"ERROR: Failed final pickling, abort!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            if self.pickle and not json_it(USER_DICT, USER_DICT_FNAME):
                sys.stderr.write(f"ERROR: Failed final pickling, abort!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            self.reset_state()
            return False

        if self.new_tweets % 100 == 0:
            print(f"currently scraped {self.new_tweets} new tweets")

    def on_error(self, status_code):
        if status_code == 420:
            # Rate Limited
            return False

    def on_exception(self, exception):
        try:
            raise exception
        except ProtocolError:
            print(
                f"Unknown protocol error, abandoning stream after {self.new_tweets} tweets"
            )
        except WantReadError:
            print(f"SSL error? Abandoning stream after {self.new_tweets} tweets")
        except TimeoutError:
            print(f"Tweet rate too low, timing out after {self.new_tweets} tweets")
        except:
            print(
                f"Unknown error {exception}, abandoning stream after {self.new_tweets} tweets"
            )
        finally:
            self.reset_state()
            return False

    def reset_state(self):
        self.new_tweets = 0
        self.new_users = 0


def expand_user_list(user_id, api_obj, count_key):
    """
    Given a user, a Twitter api object, and a dictionary key:
    Scrape twitter for that users friends/followers (depending on the key)
    and add this information back into the user dictionary.
    """
    now = dt.datetime.now()
    print(
        "(%s) (id=%s) Expanding %s"
        % (now.strftime("%a, %b %d %I:%M %p"), user_id, count_key)
    )
    user_cursor = tweepy.Cursor(api_obj, user_id=user_id)
    pages = []
    try:
        pages = list(user_cursor.pages())
    except tweepy.error.TweepError:
        print("This user has protected tweets, skipping")
    return
    for user_id_page in pages:
        users_on_page = []
        for other_user_id in user_id_page:
            users_on_page.append(other_user_id)
        USER_DICT[user_id][count_key] += users_on_page
    if not json_it(USER_DICT, USER_DICT_FNAME):
        sys.stderr.write(f"failed to pickle after processing user {user_id}")


def expand_neighbors(api):
    """
    Iterate through the user dict, scrape twitter for their friends
    and followers, and add this information back into the dictionary
    (pickling at the end).
    """
    for i, user_id in enumerate(USER_DICT):
        print(f"expanding {user_id}'s friends")
        if USER_DICT[user_id]["followers"] == 0:
            USER_DICT[user_id]["followers"] = []
        if USER_DICT[user_id]["friends"] == 0:
            USER_DICT[user_id]["friends"] = []
        num_actual_followers = len(USER_DICT[user_id]["followers"])
        num_actual_friends = len(USER_DICT[user_id]["friends"])

        num_expected_followers = USER_DICT[user_id]["followers_count"]

        num_expected_friends = USER_DICT[user_id]["friends_count"]
        if num_actual_followers == 0:
            expand_user_list(user_id, api.followers_ids, "followers")
            expand_user_list(user_id, api.friends_ids, "friends")
        elif num_actual_followers != num_expected_followers:
            print(
                f"mismatched follower count: {num_actual_followers}, but expected {num_expected_followers}"
            )
            print(f"Check userid {user_id}")
        elif num_actual_friends != num_expected_friends:
            print(
                f"mismatched follower count: {num_actual_friends}, but expected {num_expected_friends}"
            )
            print(f"Check userid {user_id}")
        print(f"finished {user_id}'s friends\n")
        if (i + 1) % 100 == 0:
            print("=====================")
            print("Processed %06d users" % (i + 1))
            print("=====================")
            print()


def stream_user_tweets():

    users = compile_users_n_others()

    api = authenticate_twitter()
    stream_listener = StreamListener(num_to_grab=-1, pickle=False)
    stream = tweepy.Stream(auth=api.auth, listener=stream_listener)
    for i, representative in enumerate(users):
        print(f"Streaming from user group {i} (representative user {representative})")
        user_set = users[representative]
        user_set.add(representative)

        def get_tweets():
            stream.filter(follow=user_set, stall_warnings=True)

        p = multiprocessing.Process(target=get_tweets)
        p.start()
        p.join(150)
        p.terminate()
        p.join()
        if (i + 1) % 50 == 0:
            if not json_it(TWEET_DICT, TWEETS_FNAME):
                sys.stderr.write(f"ERROR: Failed final pickling, abort!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)
            if not json_it(USER_DICT, USER_DICT_FNAME):
                sys.stderr.write(f"ERROR: Failed final pickling, abort!\n")
                sys.exit(FILE_NOT_FOUND_EXIT_CODE)


def main():
    global GRAB_NEW
    api = authenticate_twitter()

    if GRAB_NEW:
        stream_listener = StreamListener()
        stream = tweepy.Stream(auth=api.auth, listener=stream_listener)
        stream.filter(track=KEYWORDS, stall_warnings=True)
    expand_neighbors(api)
    stream_user_tweets()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Recieved siginterrupt, jsoning objects and exiting")
        json_it(TWEET_DICT, TWEETS_FNAME)
        json_it(USER_DICT, USER_DICT_FNAME)
        sys.exit(1)
