#! /bin/sh

# From https://www.freecodecamp.org/news/how-to-get-a-docker-container-ip-address-explained-with-examples/
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $1

