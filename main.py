import os
from collections import defaultdict

from flask import Flask, render_template, url_for
from flask_frozen import Freezer
from google.cloud import storage

GCS_BUCKET = os.environ['GCS_BUCKET']

storage_client = storage.Client()
bucket = storage_client.get_bucket(GCS_BUCKET)

packages = defaultdict(list)

for blob in bucket.list_blobs():
    package_name, file_name = blob.name.split("/")

    if file_name:
        packages[package_name].append(file_name)

app = Flask(__name__)
freezer = Freezer(app)

@app.route("/index.html")
def main_index():
    links = [
        {"url": url_for('package_index', package_name=package_name), "name": package_name}
        for package_name in sorted(packages.keys())
    ]
    return render_template("index.html", links=links)


@app.route("/<package_name>/index.html")
def package_index(package_name):
    links = [
        {"url": f"https://storage.googleapis.com/{GCS_BUCKET}/{package_name}/{file_name}", "name": file_name}
        for file_name in packages[package_name]
    ]
    return render_template("index.html", links=links)



if __name__ == "__main__":
    freezer.freeze()
