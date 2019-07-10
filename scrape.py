import datetime as dt
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


def expand_user_list(user_id, api_obj, count_key):
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
    if not pickle_it(USER_DICT, USERS_FNAME):
        sys.stderr.write(f"failed to pickle after processing user {user_id}")


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

    def on_error(self, status_code):
        if status_code == 420:
            # Rate Limited
            return False


def expand_neighbors(api):
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


def main():
    api = authenticate_twitter()

    stream_listener = StreamListener()
    stream = tweepy.Stream(auth=api.auth, listener=stream_listener)
    stream.filter(track=KEYWORDS, stall_warnings=True)
    expand_neighbors(api)


if __name__ == "__main__":
    main()
