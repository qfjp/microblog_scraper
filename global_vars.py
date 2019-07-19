from itertools import count

NUM_TWEETS_TO_GRAB = 10000
TWEETS_FNAME = "tweet_dict"
USER_DICT_FNAME = "users_dict"
USER_LIST_FNAME = "users"
USER_GRAPH_FNAME = "user_graph"
USER_FRAME_FNAME = "user_frame"
RNG_FNAME = "rng"
PLOT_FILE_NAME = "plots"

_exit_codes = count(start=1, step=1)
FILE_NOT_FOUND_EXIT_CODE = next(_exit_codes)
NO_DATA_EXIT_CODE = next(_exit_codes)
