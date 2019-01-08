import jinja2
import flask

blueprint = flask.Blueprint('filters', __name__)

@jinja2.contextfilter
@blueprint.app_template_filter()
def format_thousands_int(context, n):
    return "{0:,d}".format(long(n))

@jinja2.contextfilter
@blueprint.app_template_filter()
def format_thousands_float(context, n):
    return "{0:,.2f}".format(n)

@jinja2.contextfilter
@blueprint.app_template_filter()
def convert_bytes(context, n):
    suffix = {
      'TB': 1000 ** 4,
      'GB': 1000 ** 3,
      'MB': 1000 ** 2,
      'KB': 1000,
    }
    for k, v in sorted(suffix.items(), key=lambda x: x[1], reverse=True):
      if n / v >= 1:
        return '%.2f %s' % (float(n) / v, k)
    return '%.2f %s' % (n, 'B')
