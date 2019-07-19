import sys
from enum import Enum, auto, unique

import flask
import networkx as nx
from bokeh.embed import components
from bokeh.io import output_file, show
from bokeh.models import (BoxSelectTool, Circle, HoverTool, MultiLine, Plot,
                          Range1d, TapTool, WheelZoomTool)
from bokeh.models.graphs import (EdgesAndLinkedNodes, NodesAndLinkedEdges,
                                 from_networkx)
from bokeh.palettes import GnBu8, Plasma8, Spectral4, Spectral8
from bokeh.plotting import figure
from bokeh.resources import CDN, INLINE
from networkx.drawing.nx_agraph import graphviz_layout

from global_vars import (PLOT_FILE_NAME, TWEETS_FNAME, USER_DICT_FNAME,
                         USER_GRAPH_FNAME)
from utils import json_it, reload_json, reload_object

app = flask.Flask(__name__)
app.vars = {}

USER_DICT = None
TWEET_DICT = None
NETWORK = None
SCRIPT_DIV = None
PALETTE = GnBu8


@unique
class DataSource(Enum):
    NONE = auto()
    TWEETS = auto()
    FRIENDS = auto()
    FOLLOWERS = auto()

    def to_title(self):
        if self.name == "TWEETS":
            return " by Tweet Activity"
        elif self.name == "FRIENDS":
            return " by Number of Friends"
        elif self.name == "FOLLOWERS":
            return " by Number of Followers"
        else:
            return ""

    def __str__(self):
        return self.name.lower()


def run_tweets():
    global TWEET_DICT
    global NETWORK
    if not TWEET_DICT:
        TWEET_DICT = reload_object(TWEETS_FNAME, dict)
    if not NETWORK:
        NETWORK = reload_json(
            USER_GRAPH_FNAME, nx.DiGraph, transform=nx.node_link_graph
        )
    tweets = []
    for node in NETWORK:
        try:
            node_tweets = TWEET_DICT[str(node)]
        except KeyError:
            node_tweets = []
        if node_tweets:
            tweets.append(node_tweets[0]["text"])
        else:
            tweets.append("")
    return tweets


def run_data(d_source):
    global USER_DICT
    global TWEET_DICT
    global NETWORK
    if not USER_DICT:
        USER_DICT = reload_object(USER_DICT_FNAME, dict)
    if not TWEET_DICT:
        TWEET_DICT = reload_object(TWEETS_FNAME, dict)
    if not NETWORK:
        NETWORK = reload_json(
            USER_GRAPH_FNAME, nx.DiGraph, transform=nx.node_link_graph
        )

    values = []
    for node in NETWORK:
        try:
            node_info = USER_DICT[str(node)]
        except KeyError:
            # some nodes may not show up in the user dictionary!
            node_info = {"followers": [], "friends": []}

        if d_source in [DataSource.FRIENDS, DataSource.FOLLOWERS]:
            values.append(len(node_info[str(d_source)]))
        elif d_source == DataSource.TWEETS:
            try:
                num_tweets = len(TWEET_DICT[str(node)])
                values.append(num_tweets)
            except KeyError:
                values.append(0)
        else:
            values.append(1)

    maximum = max(values)
    minimum = min(values)

    colors = []
    sizes = []
    for value in values:
        index_ratio = (value - minimum) / maximum
        color_index = int(index_ratio * (len(PALETTE) - 1))
        sizes.append(2 ** (color_index + 1))
        colors.append(PALETTE[color_index])
    return sizes, colors


def get_square_bounds():
    global NETWORK
    if not NETWORK:
        NETWORK = reload_json(
            USER_GRAPH_FNAME, nx.DiGraph, transform=nx.node_link_graph
        )
    positions = graphviz_layout(NETWORK, prog="sfdp")
    xs = []
    ys = []
    for node in positions:
        cur_x, cur_y = positions[node]
        xs.append(cur_x)
        ys.append(cur_y)

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x_range = max_x - min_x
    y_range = max_y - min_y
    x_center = (max_x + min_x) / 2
    y_center = (max_y + min_y) / 2

    if x_range > y_range:
        extra = x_range * 0.1
        min_y = y_center - (x_range / 2) - extra
        max_y = y_center + (x_range / 2) + extra
        min_x -= extra
        max_x += extra
    else:
        extra = y_range * 0.1
        min_x = x_center - (y_range / 2) - extra
        max_x = x_center + (y_range / 2) + extra
        min_y -= extra
        max_y += extra
    return (min_x, max_x), (min_y, max_y)


def make_plottable(colors=None, sizes=None, tweets=None):
    global NETWORK
    if not NETWORK:
        NETWORK = reload_json(
            USER_GRAPH_FNAME, nx.DiGraph, transform=nx.node_link_graph
        )
    graph = from_networkx(NETWORK, graphviz_layout, prog="sfdp")

    if not colors:
        node_color = Spectral4[0]
    else:
        node_color = "color"
        graph.node_renderer.data_source.add(colors, "color")

    if not sizes:
        node_size = 8
    else:
        node_size = "size"
        graph.node_renderer.data_source.add(sizes, "size")

    if tweets:
        graph.node_renderer.data_source.add(tweets, "desc")

    edge_width = 0.3
    select_edge_width = 2
    node_alpha = 0.95
    edge_alpha = 0.3
    edge_color = "#666666"
    select_color = Spectral4[2]
    hover_color = Spectral4[1]

    graph.node_renderer.glyph = Circle(
        size=node_size,
        fill_color=node_color,
        fill_alpha=node_alpha,
        line_color=node_color,
        line_alpha=node_alpha,
    )
    graph.node_renderer.selection_glyph = Circle(
        size=node_size, fill_color=select_color, line_color=select_color
    )
    graph.node_renderer.hover_glyph = Circle(
        size=node_size, fill_color=hover_color, line_color=hover_color
    )

    graph.edge_renderer.glyph = MultiLine(
        line_color=edge_color, line_alpha=edge_alpha, line_width=edge_width
    )
    graph.edge_renderer.selection_glyph = MultiLine(
        line_color=select_color, line_width=select_edge_width
    )
    graph.edge_renderer.hover_glyph = MultiLine(
        line_color=hover_color, line_width=select_edge_width
    )
    graph.selection_policy = NodesAndLinkedEdges()
    graph.inspection_policy = NodesAndLinkedEdges()

    return graph


def construct_js_css():
    global SCRIPT_DIV
    SCRIPT_DIV = reload_json(PLOT_FILE_NAME, lambda: None)

    if SCRIPT_DIV:
        return

    SCRIPT_DIV = {}
    for name, d_source in DataSource.__members__.items():
        tweets = run_tweets()
        sizes, colors = run_data(d_source)
        graph = make_plottable(colors=colors, sizes=sizes, tweets=tweets)

        tooltips = []
        if tweets:
            tooltips.append(("tweets", "@desc"))
        else:
            tooltips = None
        x_range, y_range = get_square_bounds()
        plot = figure(
            title="User Graph" + d_source.to_title(),
            x_range=x_range,
            y_range=y_range,
            plot_width=800,
            plot_height=800,
        )
        plot.background_fill_color = "black"
        plot.background_fill_alpha = 0.9
        plot.axis.visible = False
        plot.grid.visible = False
        plot.add_tools(
            HoverTool(tooltips=tooltips), TapTool(), BoxSelectTool(), WheelZoomTool()
        )
        plot.renderers.append(graph)
        script, div = components(plot)
        SCRIPT_DIV[str(d_source)] = (script, div)
    json_it(SCRIPT_DIV, PLOT_FILE_NAME)


@app.route("/index", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def plot_page():
    global SCRIPT_DIV
    construct_js_css()

    d_source = DataSource.NONE
    if flask.request.method == "POST":
        data_form = flask.request.form.get("Data")
        if data_form == "none":
            d_source = DataSource.NONE
        elif data_form == "followers":
            d_source = DataSource.FOLLOWERS
        elif data_form == "friends":
            d_source = DataSource.FRIENDS
        elif data_form == "tweets":
            d_source = DataSource.TWEETS
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    script, div = SCRIPT_DIV[str(d_source)]
    return flask.render_template(
        "plot.html",
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
    )


def main():
    app.run(port=33507, debug=True)
if __name__ == "__main__":
    main()


# output_file("networkx_graph.html")
# show(plot)
