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

def create_pypi(packages):
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

    freezer.freeze()
    shutil.make_archive("site", 'zip', freezer.root)

def main():
    print("Reading GCS bucket.")
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(GCS_BUCKET)

    packages = defaultdict(list)

    for blob in bucket.list_blobs():
        package_name, file_name = blob.name.split("/")

        if file_name:
            packages[package_name].append(file_name)

    print("Freezing PIP repository.")
    create_pypi(packages)

    print("Creating site archive.")
    with open("site.zip", 'rb') as site_zip:
        site_zip_data = site_zip.read()

    print("Deploying archive to Netlify.")
    response = requests.post(
        f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_URL}/deploys",
        headers={"Content-Type": "application/zip", "Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}"},
        data=site_zip_data
    )
    response_data = response.json()
    deployment_id = response_data['id']

    print("Waiting for deployment to be available.")
    deployment_ready = False

    while not deployment_ready:
        response = requests.get(
            f"https://api.netlify.com/api/v1/deploys/{deployment_id}",
            headers={"Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}"}
        )
        response_data = response.json()
        deployment_ready = response_data["state"] == "ready"

    print("Deployment complete!")

def gcf_proxy(event, context):
    _ = event
    _ = context
    main()

if __name__ == "__main__":
    main()
