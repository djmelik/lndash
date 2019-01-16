from flask import Blueprint
from jinja2 import contextfilter

blueprint = Blueprint("filters", __name__)


@contextfilter
@blueprint.app_template_filter()
def format_thousands_int(context, n):
    return "{0:,d}".format(int(n))


@contextfilter
@blueprint.app_template_filter()
def format_thousands_float(context, n):
    return "{0:,.2f}".format(n)


@contextfilter
@blueprint.app_template_filter()
def convert_bytes(context, n):
    # keep the following list sorted
    suffixes = [("TB", 1000 ** 4), ("GB", 1000 ** 3), ("MB", 1000 ** 2), ("KB", 1000)]
    for k, v in suffixes:
        if n / v >= 1:
            return "%.2f %s" % (float(n) / v, k)
    return "%.2f %s" % (n, "B")
