# pychat-stock

A simple chat application assignment

## Objective

This is an application that have the following requirements:

* Allow registered users to log in and talk with other users in a chatroom

* Allow users to post messages as commands into the chatroom with the format `/stock=<stock code>`, which will be parsed by a decoupled bot that will call an API for obtaining the stock value

* Have the chat messages ordered by their timestamps, showing only the last 50 messages

## Running

The project is organized as a [Docker Compose](https://docs.docker.com/compose/) environment that will run the application Docker containers (chat and bot), and the backend dependencies (Redis and RabbitMQ). The machine that will run the project should have Docker and Docker Compose installed (the machine I used for development has Docker 20.10 and Docker-Compose 1.27). To run the project it is a simple case of running `docker-compose up -d`, and to deactivate after it `docker-compose down`. If you want to take a look at the logs as they progress, only use `docker-compose up`, and press Ctrl+C to destroy the cluster - pressing again will probably be needed since some open connections may leave the system hanging.

This project was developed under an Ubuntu 20.04 machine.

### Executing the client

![Base usage](https://github.com/ghapereira/pychat-stock/blob/main/static/baseusage.gif)

To execute the client, open in a browser the HTML file at `pychat-stock/static/login.html`. There, the page contains four sections:

* On the top, a session containing name and password fields, and a send button. This is the login session, before doing anything else please make a login. If you are using the default-provided `db.sql` there are two user/password combinations: user `plutothedog` with password `1234` and `john` with password `doe`.

* The second session contains the available chatrooms. When logging in, the application will send a GET request to the `/v1/chatroom` endpoint and fill in a list of available chatrooms. If using the default db, there will be two available chatrooms with some conversations on it. The user must single-click on any of them to
set the value of the chatroom to the next section.

* The third section contains the chatroom conversations. After clicking on an available one on the past section it will be put into the "chatroom" text field and updated with the conversations. There is a "Refresh" button near to it because the server is NOT communicating with the front actively with, for example, websockets, so it falls on the client to periodically refresh the conversations itself.

* On the fourth and last section an user can type a message and send it

### Creating more items

## Architecture

The architecture was projected to meet the given requirements. There are five listed Docker containers in the `docker-compose.yml` definition file:

* **chat**: Is the main container that serves the application. Based on the FastAPI container, it serves on the port 8000 of localhost. All client communications must happen against it.

* **bot**: From a base Python container, this one listens to the _requeststock_ queue on the **rabbitmq** container for stock requests; when one comes it fetch stock data from an external API, parses this data and then posts this result back to the _publishstock_ queue, for publishing to the appropriate chatroom.

* **botposter**: Reads from the _publishstock_ queue and posts a message to the correspondent chatroom at **chat**. This function could theoretically be done by **chat** itself, but I found that leaving a dedicated container to be listening from the queue would free responsibilities and avoid potetial blocks from it.

* **redis**: Redis cache. Used for storing login tokens, so users may be logged off after a period of inactivity - they need to refresh a token periodically, or login again.

* **rabbitmq**: RabbitMQ container, in this case used to provide AMQP queues. It is used to decouple the main server from the bot, as requested.

Other than the containers the other components that are present are a sqlite database, used for persisting information, and the static files of the frontend.

### Flows

### Architectural considerations

* The decision for passing the headers for both username (that should be user id - see in **Security considerations**) and session id are due to allow for a same user to be concurrently logged in in multiple environments.


## Test collection

There is a Postman collection present on the **postman** directory. There, one can import the **PyChat Stock v1.postman_collection.json** file on Postman, and the local and global variables, respectively, from **LOCAL.postman_environment.json** and **My Workspace.postman_globals.json**. After selecting the corresponding environments, this collection can be used for quickly testing the application, via creating chatrooms and users and then logging in, posting messages and reading from the chatrooms.

## Security considerations

As a simple project with a strict timeframe, many security issues are present. Some of them are listed in the following topics:

* The worst offense of the whole project is that it DOES NOT use HTTPS. As requests will be trafficking in plaintext, it is really easy to obtain passwords and confidential information from this system. If any security measure would need to be taken here this is certainly the priority.

* Running a custom-made login flow while having available solutions as Oauth, for example, is really bad. The login flow here is used only to illustrate a feasible system, nothing else. Cloud providers IAM systems also are better employed for this.

* For token validation during the various flows the system passes username and token all the time. This is really bad; user uuid should be used instead, so the username would be used only once, for login, and then an internal system information would be used, so an attacker wouldn't have so easily available an username.

* Some endpoints such as user creation and chatroom creation, among others, are left free for use unauthenticated. This is done for simplicity, but it is obvious that such actions SHOULD NOT be left this way.

* The database is stored unencrypted and without a password for accessing it. User password is left hashed (and salted), and this is probably the only somewhat serious protection on the whole system, but as stated above password travels unencrypted on the network for login, so it's not a strong protection.

* On some instances database records ids travel in the network among requests. One should NEVER use database records ids as keys outside it, since this leaves open internal details for attackers.

* For the simplicity of the front-end, allowing it to run from localhost against the server, it ignores CORS. This is a BAD practice also.

* In the Docker Compose it is used a dependency feature so the containers that use the queue will not start before it. Starting, however, isn't the same as _being ready_. In this way, it's possible that the containers that use the queue are ready before the queue, and so an eager client would make requests when it's not ready yet. The right way to deal with this is to implement a retry logic, so the clients would retry until the queue is ready. Since I had a short time to implement this I'm simply adding a delay of 15 seconds for the clients, so they will wait this time, one that the queue will be on as per my experiments. This is bad because in a slower environment this may not be the case.

## What's missing?

As of v1.2:

* Moving application logic from the controller on **chat** to a "services" component

* Adding automated tests
