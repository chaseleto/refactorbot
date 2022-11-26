docker run -d \
  -p 9001:9001 \
  --name portainer_agent_1 \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:2.16.1

docker run -d \
  -p 9002:9002 \
  --name portainer_agent_2 \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:2.16.1