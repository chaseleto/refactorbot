sudo rm -r /opt/docker/discordbot_data/src
export MONGO_USER=$(gcloud secrets versions access latest --secret="MONGO_USER") && \
export MONGO_PASSWORD=$(gcloud secrets versions access latest --secret="MONGO_PASSWORD") && \
export DISCORD_SECRET=$(gcloud secrets versions access latest --secret="DISCORD_SECRET") && \
cd /refactorbot/ && \
sudo git pull  && \
sudo cp -Rp src /opt/docker/discordbot_data/src/ && \
sudo ./scripts/volumes.sh && \
sudo docker compose -f smoot-compose.yml up -d