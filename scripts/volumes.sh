VOL1=lavalink_data
VOL2=discordbot_data

DIR1_EXISTS=$(ls /opt/docker/$VOL1 | grep $VOL1)
DIR2_EXISTS=$(ls /opt/docker/$VOL2 | grep $VOL2)

VOL1_EXISTS=$(docker volume ls | grep $VOL1)
VOL2_EXISTS=$(docker volume ls | grep $VOL2)




if [ -z "$DIR1_EXISTS" ]; then
    echo "creating /opt/docker/$VOL1.."
    sudo mkdir -p /opt/docker/$VOL1
fi

if [ -z "$DIR2_EXISTS" ]; then
    echo "creating /opt/docker/$VOL2.."
    sudo mkdir -p /opt/docker/$VOL2
fi

if [ -z "$VOL1_EXISTS" ]; then
    docker volume create --driver local \
    --opt type=none \
    --opt device=/opt/docker/$VOL1/ \
    --opt o=bind $VOL1

fi

if [ -z "$VOL2_EXISTS" ]; then
docker volume create --driver local \
    --opt type=none \
    --opt device=/opt/docker/$VOL2/ \
    --opt o=bind $VOL2
fi

# Copy source code to the volume
sudo cp -Rp src /opt/docker/discordbot_data/src/
sudo cp -Rp lavalink /opt/docker/lavalink_data/lavalink/