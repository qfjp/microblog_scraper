import random
import sys
from enum import Enum, unique
from statistics import mean, stdev

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from networkx.drawing.nx_agraph import to_agraph

from global_vars import (NO_DATA_EXIT_CODE, TWEETS_FNAME, USER_GRAPH_FNAME,
                         USERS_FNAME)
from utils import pickle_it, reload_object

USER_DICT = reload_object(USERS_FNAME, dict)

STDEV_MOD = 4
OTHERS_MOD = 0.0001



@unique
class Direct(Enum):
    IN = True
    OUT = False

    def twit_key(self):
        if self.name == "IN":
            return "followers"
        elif self.name == "OUT":
            return "friends"

    def deg_view(self, graph):
        if self.name == "IN":
            return graph.in_degree
        elif self.name == "OUT":
            return graph.out_degree

    def make_edge(self, user, other):
        if self.name == "IN":
            return (other, user)
        elif self.name == "OUT":
            return (user, other)


def get_bounds(graph, user_id, direct=Direct.IN):
    try:
        num = direct.deg_view(graph)[user_id]
    except KeyError:
        num = 0

    try:
        expected = len(USER_DICT[user_id][direct.twit_key()])
    except TypeError:
        sys.stderr.write(f"Unexpected type for {direct.twit_key()} list on {user_id}")
        expected = 0
    return num, expected


def build_graph(pickle=True, from_scratch=False):
    if not from_scratch:
        print("Loading graph data.")
        user_graph = reload_object(USER_GRAPH_FNAME, nx.DiGraph)
        if user_graph:
            return user_graph
    print("Building graph...")
    if not USER_DICT:
        sys.stderr.write("ERROR:  A user or tweet dictionary is empty.")
        sys.exit(NO_DATA_EXIT_CODE)

    for i, user_id in enumerate(USER_DICT):
        new_edges = {Direct.IN: [], Direct.OUT: []}
        for direct in (Direct.IN, Direct.OUT):
            num, expected = get_bounds(user_graph, user_id, direct=direct)
            if num == 0:
                others = USER_DICT[user_id][direct.twit_key()]
                for ident in others:
                    edge = direct.make_edge(user_id, ident)
                    new_edges[direct].append(edge)
            elif num != expected:
                print(
                    f"followers mismatch for node {user_id}: {num}, {expected}, {direct}"
                )
                print("Skipping")
                print()
        new_in = new_edges[Direct.IN]
        new_out = new_edges[Direct.OUT]
        if len(new_in) == 0 or len(new_out) == 0:
            print(
                f"Either no in edges ({new_in}), or no out edges ({new_out}) for {user_id}"
            )
        else:
            user_graph.add_edges_from(new_in)
            user_graph.add_edges_from(new_out)

        if (i + 1) % 100 == 0:
            print(f"Analyzed %d users" % (i + 1))
    if pickle:
        pickle_it(user_graph, USER_GRAPH_FNAME)
    return user_graph


def trim_graph(graph, reduce_sample=True):
    print("Trimming graph...")
    significant_ids = set()
    for direct in (Direct.IN, Direct.OUT):
        sample = []
        ids = []
        for user_id in graph:
            ids.append(user_id)
            num_in = direct.deg_view(graph)[user_id]
            sample.append(num_in)
        sample_mean = mean(sample)
        pop_stdev = stdev(sample)
        for i, degree in enumerate(sample):
            if abs(degree - sample_mean) > STDEV_MOD * pop_stdev:
                user_id = ids[i]
                significant_ids.add(user_id)

        extras = set()
        for user_id in significant_ids:
            try:
                others = set(USER_DICT[user_id][direct.twit_key()])
            except KeyError:
                continue
            if reduce_sample:
                others = random.sample(others, int(len(others) * OTHERS_MOD))
            extras = extras.union(others)

        significant_ids = significant_ids.union(extras)

    return graph.subgraph(significant_ids)


def main():
    graph = build_graph(pickle=True)
    small_graph = trim_graph(graph)
    print(len(graph), len(small_graph))
    # plot_histo(small_graph)

    # nx.write_gexf(small_graph, "test.gexf")
    a = to_agraph(small_graph)
    with open("graph.dot", "w") as dot_file:
        dot_file.write(str(a))


if __name__ == "__main__":
    main()
