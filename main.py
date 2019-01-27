import sys

if sys.version_info.major != 3:
    raise OSError("Python 3 is required")

from flask import Flask

import filters
import views
from cache import cache

app = Flask(__name__)
app.register_blueprint(filters.blueprint)
app.register_blueprint(views.blueprint)
app.debug = False
app.testing = False

cache.init_app(app)

if __name__ == "__main__":
    app.run()
