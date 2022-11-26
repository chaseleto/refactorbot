
function startup {
    chmod +x scripts/docker_install.sh && \
    chmod +x scripts/volumes.sh && \
    chmod +x scripts/portainer.sh && \
    ./scripts/docker_install.sh -y && \ # add logic to check if docker is installed first
    ./scripts/volumes.sh && \
    ./scripts/portainer.sh && \  # portainer used for ease of monitoring
    docker compose -f smoot-compose.yml up -d
}

apt install jq -y && \
export MONGO_USER=$(gcloud secrets versions access latest --secret="MONGO_USER") && \
export MONGO_PASSWORD=$(gcloud secrets versions access latest --secret="MONGO_PASSWORD") && \
export DISCORD_SECRET=$(gcloud secrets versions access latest --secret="DISCORD_SECRET") && \

apt-get update -y && \
apt install git -y && \
smoot_exists=$(ls | grep refactorbot )

if [ -z "$smoot_exists" ]; then
    sudo git clone https://github.com/chaseleto/refactorbot.git
    cd refactorbot
    startup
else 
    cd refactorbot
    git pull 
    echo "y" | startup
fi