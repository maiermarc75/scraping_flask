import sentry_sdk
from flask import Flask, redirect, render_template, request, url_for
from sentry_sdk.integrations.flask import FlaskIntegration

from scrape import get_scraping_data
from scrape.floorplan import Floorplan

sentry_sdk.init(
    dsn="https://a66c6ce9d612438289d0cff0d9f2efa6@o4504262732808192.ingest.sentry.io/4504262849593347",
    integrations=[
        FlaskIntegration(),
    ],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

app = Flask(__name__)


scraping_data = {}


@app.route("/")
def index():
    return render_template("index.html", property_info=scraping_data)


@app.route("/scrap", methods=["POST"])
def scrap():
    global scraping_data
    _url = request.form.get("url")
    # scraping_data = get_scraping_data(_url)
    scraping_data = Floorplan().run(_url)
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(error):
    return redirect(url_for("index"))


app.run(host="0.0.0.0", debug=True)
