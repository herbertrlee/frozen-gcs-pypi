import os
import shutil
from collections import defaultdict

import requests
from flask import Flask, render_template, url_for
from flask_frozen import Freezer
from google.cloud import storage

GCS_BUCKET = os.environ['GCS_BUCKET']
NETLIFY_SITE_URL = os.environ['NETLIFY_SITE_URL']
NETLIFY_ACCESS_TOKEN = os.environ['NETLIFY_ACCESS_TOKEN']

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


def main():
    freezer.freeze()
    shutil.make_archive("site", 'zip', freezer.root)

    with open("site.zip", 'rb') as site_zip:
        site_zip_data = site_zip.read()

    response = requests.post(
        f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_URL}/deploys",
        headers={"Content-Type": "application/zip", "Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}"},
        data=site_zip_data
    )

    print(response.status_code)

if __name__ == "__main__":
    main()
