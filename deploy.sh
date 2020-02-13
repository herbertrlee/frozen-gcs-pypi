#!/usr/bin/env bash

gcloud functions deploy pypi-reindex-1 \
  --runtime python37 \
  --trigger-resource ${GCS_BUCKET} \
  --trigger-event google.storage.object.finalize \
  --entry-point main \
  --set-env-vars GCS_BUCKET=${GCS_BUCKET},NETLIFY_SITE_URL=${NETLIFY_SITE_URL},NETLIFY_ACCESS_TOKEN=${NETLIFY_ACCESS_TOKEN}
