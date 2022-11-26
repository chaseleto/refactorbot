# accepts public keyfile path as required argument
key_file=$1

# list keys
gcloud compute project-info describe --format="value(commonInstanceMetadata[items][ssh-keys])"

# add to project
gcloud compute project-info add-metadata --metadata-from-file=ssh-keys=key_file

# add to innstance
gcloud compute instances add-metadata discordbot --metadata-from-file ssh-keys=key_file

# add to os login for compute instances..?
gcloud compute os-login ssh-keys add --key-file=key_file --project=pragmatic-ruler-369222