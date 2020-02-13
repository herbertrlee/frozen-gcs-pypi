import os
import shutil
import uuid
from collections import defaultdict

import requests
from flask import Flask, render_template, url_for
from flask_frozen import Freezer
from google.cloud import storage

GCS_BUCKET = os.environ['GCS_BUCKET']
NETLIFY_SITE_URL = os.environ['NETLIFY_SITE_URL']
NETLIFY_ACCESS_TOKEN = os.environ['NETLIFY_ACCESS_TOKEN']

def create_pypi(packages, build_folder):
    app = Flask(__name__)
    app.config['FREEZER_DESTINATION'] = f"{build_folder}/build"
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
    return shutil.make_archive(f"{build_folder}/site", 'zip', base_dir=freezer.root)

def main(event, context):
    _ = event
    _ = context

    print("Reading GCS bucket.")
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(GCS_BUCKET)

    packages = defaultdict(list)

    for blob in bucket.list_blobs():
        package_name, file_name = blob.name.split("/")

        if file_name:
            packages[package_name].append(file_name)

    print("Creating build folder.")
    random_string = uuid.uuid4().hex
    build_folder = f"/tmp/{random_string}"

    print("Freezing PIP repository.")
    archive_path = create_pypi(packages, build_folder)

    print("Creating site archive.")
    with open(archive_path, 'rb') as site_zip:
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

    print("Deployment complete! Cleaning up build folder.")
    shutil.rmtree(build_folder)

if __name__ == "__main__":
    main(None, None)
