import sys

import networkx as nx
import tweepy

from global_vars import (NO_DATA_EXIT_CODE, TWEETS_FNAME, USER_GRAPH_FNAME,
                         USERS_FNAME)
from utils import authenticate, pickle_it, reload_object


def main():
    user_graph = nx.DiGraph()
    api = authenticate()
    user_dict = reload_object(USERS_FNAME, bool)
    tweet_dict = reload_object(TWEETS_FNAME, bool)

    if not user_dict or not tweet_dict:
        sys.stderr.write("ERROR:  A user or tweet dictionary is empty.")
        sys.exit(NO_DATA_EXIT_CODE)

    for i, user_id in enumerate(user_dict):
        follower_cursor = tweepy.Cursor(api.followers_ids, user_id=user_id)
        for follower_id_page in follower_cursor.pages():
            for follower_id in follower_id_page:
                user_graph.add_edge(user_id, follower_id)
        followed_cursor = tweepy.Cursor(api.friends_ids, user_id=user_id)
        for followed_id_page in followed_cursor.pages():
            for followed_id in followed_id_page:
                user_graph.add_edge(followed_id, user_id)
        if i % 100 == 0:
            print(f"Analyzed {i} users")
    pickle_it(user_graph, USER_GRAPH_FNAME)


if __name__ == "__main__":
    main()
