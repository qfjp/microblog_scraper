import random
import sys
from enum import Enum, unique
from statistics import mean, stdev

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import ujson
from networkx.drawing.nx_agraph import to_agraph

from global_vars import (NO_DATA_EXIT_CODE, RNG_FNAME, TWEETS_FNAME,
                         USER_DICT_FNAME, USER_FRAME_FNAME, USER_GRAPH_FNAME)
from utils import json_it, pickle_it, reload_json, reload_object

USER_FRAME = pd.DataFrame(reload_json(USER_DICT_FNAME, dict)).transpose()

friends = USER_FRAME["friends"]
followers = USER_FRAME["followers"]
with_friends = USER_FRAME.loc[USER_FRAME["friends"].astype(bool)]
VALID_USER_FRAME = with_friends.loc[with_friends["followers"].astype(bool)]
USER_LIST = VALID_USER_FRAME.axes[0]

STDEV_MOD = 1
OTHERS_MOD = 0.001


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


def get_expected_connection_bounds(graph, user_id, direct=Direct.IN):
    try:
        num = direct.deg_view(graph)[user_id]
    except KeyError:
        num = 0

    try:
        expected = len((VALID_USER_FRAME.loc[user_id])[direct.twit_key()])
    except TypeError:
        sys.stderr.write(f"Unexpected type for {direct.twit_key()} list on {user_id}")
        expected = 0
    return num, expected


def build_graph(pickle=False, from_scratch=True):
    user_graph = nx.DiGraph()
    if not from_scratch:
        print("Loading graph data.")
        user_graph = reload_object(USER_GRAPH_FNAME, nx.DiGraph)
        if user_graph:
            return user_graph
    print("Building graph...")
    if VALID_USER_FRAME.empty:
        sys.stderr.write("ERROR:  A user or tweet dictionary is empty.")
        sys.exit(NO_DATA_EXIT_CODE)

    for i, user_id in enumerate(USER_LIST):
        new_edges = {Direct.IN: [], Direct.OUT: []}
        for direct in (Direct.IN, Direct.OUT):
            num, expected = get_expected_connection_bounds(
                user_graph, user_id, direct=direct
            )
            if num == 0:
                others = (VALID_USER_FRAME.loc[user_id])[direct.twit_key()]
                for ident in others:
                    edge = direct.make_edge(int(user_id), int(ident))
                    new_edges[direct].append(edge)
            elif num != expected:
                print(
                    f"followers mismatch for node {user_id}: {num}, {expected}, {direct}"
                )
                print("Skipping")
                print()
        new_in = new_edges[Direct.IN]
        new_out = new_edges[Direct.OUT]
        if len(new_in) != 0 or len(new_out) != 0:
            user_graph.add_edges_from(new_in)
            user_graph.add_edges_from(new_out)

        if (i + 1) % 100 == 0:
            print(f"Analyzed %d users" % (i + 1))
    if pickle:
        pickle_it(user_graph, FULL_GRAPH_FNAME)
    return user_graph


def trim_graph(graph, reduce_sample=True, pickle=True, from_scratch=True):
    if not graph and not from_scratch:
        graph = reload_json(USER_GRAPH_FNAME, transform=nx.node_link_graph)
        return graph

    rng_state = reload_object(RNG_FNAME, random.getstate)
    random.setstate(rng_state)
    print("Trimming graph...")
    significant_id_set = set()

    for direct in (Direct.IN, Direct.OUT):
        sample = []
        ids = []
        for user_id in graph:
            ids.append(user_id)
            num_neighb = direct.deg_view(graph)[user_id]
            sample.append(num_neighb)
        sample_mean = mean(sample)
        pop_stdev = stdev(sample)
        for i, degree in enumerate(sample):
            if abs(degree - sample_mean) > STDEV_MOD * pop_stdev:
                user_id = ids[i]
                significant_id_set.add((user_id, degree))

    by_asc_degree = sorted(list(significant_id_set), key=lambda x: x[1])
    significant_ids = [i[0] for i in by_asc_degree]

    to_subgraph = set()
    for user_id in significant_ids:
        try:
            others = set(graph.neighbors(user_id))
        except KeyError:
            continue
        if reduce_sample and len(others) != 0:
            others = random.sample(others, int(len(others) * OTHERS_MOD))

        if len(others) == 0:
            continue

        to_subgraph.add(user_id)
        for other in others:
            to_subgraph.add(other)

    pickle_it(rng_state, RNG_FNAME)

    user_graph = graph.subgraph(to_subgraph)

    if pickle:
        json_it(user_graph, USER_GRAPH_FNAME, nx.node_link_data)

    return user_graph


def main():
    graph = build_graph(pickle=False, from_scratch=True)
    small_graph = trim_graph(graph, pickle=False, from_scratch=True)
    small_graph.name = "Twitter User Graph"
    print(f"full graph: {len(graph)} nodes")
    print(f"trim graph: {len(small_graph)} nodes")
    print("Generating JSON")
    json_it(small_graph, USER_GRAPH_FNAME, nx.node_link_data)


if __name__ == "__main__":
    main()
