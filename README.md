# pychat-stock

A simple chat application assignment

## Objective

This is an application that have the following requirements:

* Allow registered users to log in and talk with other users in a chatroom

* Allow users to post messages as commands into the chatroom with the format `/stock=<stock code>`, which will be parsed by a decoupled bot that will call an API for obtaining the stock value

* Have the chat messages ordered by their timestamps, showing only the last 50 messages

## Running

The project is organized as a [Docker Compose](https://docs.docker.com/compose/) environment that will run the application Docker containers (chat and bot), and the backend dependencies (Redis and RabbitMQ). The machine that will run the project should have Docker and Docker Compose installed (the machine I used for development has Docker 20.10 and Docker-Compose 1.27). To run the project it is a simple case of running `docker-compose up -d`, and to deactivate after it `docker-compose down`.

