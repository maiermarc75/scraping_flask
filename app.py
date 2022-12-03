from flask import Flask, redirect, render_template, request, url_for
from repli360 import ScrapingEngine

app = Flask(__name__)

property_info = {}


@app.route("/")
def index():
    return render_template("index.html", property_info=property_info)


@app.route("/scrap", methods=["POST"])
def scrap():
    global property_info
    _url = request.form.get("url")
    scrapobj = ScrapingEngine()
    property_info = scrapobj.run(_url)
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(error):
    return redirect(url_for("index"))


app.run(host="0.0.0.0", debug=True)
