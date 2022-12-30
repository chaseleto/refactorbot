sudo rm -r /opt/docker/discordbot_data/src && \
cd /refactorbot/ && \
sudo git pull  && \
sudo cp -Rp src /opt/docker/discordbot_data/src/ && \
sudo ./scripts/volumes.sh && \
export DISCORD_SECRET=$(gcloud secrets versions access latest --secret="DISCORD_SECRET") && \
sudo docker compose -f smoot-compose.yml up -d