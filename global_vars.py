from itertools import count

NUM_TWEETS_TO_GRAB = 10000
TWEETS_FNAME = "tweet_dict.pkl"
USERS_FNAME = "users_dict.pkl"
USER_GRAPH_FNAME = "user_graph.pkl"

_exit_codes = count(start=1, step=1)
FILE_NOT_FOUND_EXIT_CODE = next(_exit_codes)
NO_DATA_EXIT_CODE = next(_exit_codes)
