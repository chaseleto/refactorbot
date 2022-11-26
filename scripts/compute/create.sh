gcloud compute instances create discordbot \
--image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20221101a \
--service-account smoot-service-account@pragmatic-ruler-369222.iam.gserviceaccount.com \
--scopes=cloud-platform,storage-full \
--project=pragmatic-ruler-369222 \
--zone=us-central1-a \
--machine-type=e2-standard-2 \
--address=34.171.240.203 \
--metadata=startup-script-url=gs://lavalink-bucket100/user_data.sh \
--tags="http-server,https-server"