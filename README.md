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

![Running docker-compose](https://github.com/ghapereira/pychat-stock/blob/main/static/docker-compose.gif)

### Executing the client

![Base usage](https://github.com/ghapereira/pychat-stock/blob/main/static/baseusage.gif)

To execute the client, open in a browser the HTML file at `pychat-stock/static/login.html`. There, the page contains four sections:

* On the top, a session containing name and password fields, and a send button. This is the login session, before doing anything else please make a login. If you are using the default-provided `db.sql` there are two user/password combinations: user `plutothedog` with password `1234` and `john` with password `doe`.

* The second session contains the available chatrooms. When logging in, the application will send a GET request to the `/v1/chatroom` endpoint and fill in a list of available chatrooms. If using the default db, there will be two available chatrooms with some conversations on it. The user must single-click on any of them to
set the value of the chatroom to the next section.

* The third section contains the chatroom conversations. After clicking on an available one on the past section it will be put into the "chatroom" text field and updated with the conversations. There is a "Refresh" button near to it because the server is NOT communicating with the front actively with, for example, websockets, so it falls on the client to periodically refresh the conversations itself.

* On the fourth and last section an user can type a message and send it to the chatroom. After posting the message the client will refresh the messages. If other messages were posted in the meantime by, say, other users or the bot they will be visible there.

### Creating more items

If you don't want to use the basic provided database, or if you want to create other items, there are endpoints for creation of chatrooms, users and messages. They are better described in the Postman collection or in the Swagger documentation that is available on the FastAPI server when it's running on [http://127.0.0.1:8000/docs#/](http://127.0.0.1:8000/docs#/). Create user and create chatroom are available without authentication, so in tests user/chatroom creation is fast.

If you want to simply drop the provided database file and restart the server, that's ok: the sqlalchemy ORM system will create a new schema, and no prior information is needed for the system to work - of course, no logins and messages are thus possible!

## Architecture

The architecture was projected to meet the given requirements. There are five listed Docker containers in the `docker-compose.yml` definition file:

* **chat**: Is the main container that serves the application. Based on the FastAPI container, it serves on the port 8000 of localhost. All client communications must happen against it.

* **bot**: From a base Python container, this one listens to the _requeststock_ queue on the **rabbitmq** container for stock requests; when one comes it fetch stock data from an external API, parses this data and then posts this result back to the _publishstock_ queue, for publishing to the appropriate chatroom.

* **botposter**: Reads from the _publishstock_ queue and posts a message to the correspondent chatroom at **chat**. This function could theoretically be done by **chat** itself, but I found that leaving a dedicated container to be listening from the queue would free responsibilities and avoid potetial blocks from it.

* **redis**: Redis cache. Used for storing login tokens, so users may be logged off after a period of inactivity - they need to refresh a token periodically, or login again.

* **rabbitmq**: RabbitMQ container, in this case used to provide AMQP queues. It is used to decouple the main server from the bot, as requested.

Other than the containers the other components that are present are a sqlite database, used for persisting information, and the static files of the frontend.

### Flows

#### Login

![Login flow](https://github.com/ghapereira/pychat-stock/blob/main/static/login_flow.png)

#### Message

![Message flow](https://github.com/ghapereira/pychat-stock/blob/main/static/message_flow.png)

#### Stock message

![Stock message flow](https://github.com/ghapereira/pychat-stock/blob/main/static/message_bot_flow.png)


### Architectural considerations

* The decision for passing the headers for both username (that should be user id - see in **Security considerations**) and session id are due to allow for a same user to be concurrently logged in in multiple environments.

* There are possible places for parallelism. The **chat** service is not tightly attached to anything but the database. If an external database was to be used, not even this. So multiple autoscaled **chat** services could exist. Web caches could be used to serve front-end and allow for this autoscaling to be transparent under it. The queues could be used to throttle requests on a high usage scenario.

* The **botposter** service exists with the sole purpose of POSTing back messages from the queue to the main **chat** service. If there was, and I knew about, a way to do this directly from the queue I would do. In a cloud environment, however, there would be no need for this: a simple serverless function (AWS Lambda, Azure Functions, GCP Cloud Functions) would do the trick in an escalable way. Of course, if usage would be extreme this could incur in a high cost, but the possibility is at least worth investigating.

* In the Docker Compose it is used a dependency feature so the containers that use the queue will not start before it. Starting, however, isn't the same as _being ready_. In this way, it's possible that the containers that use the queue are ready before the queue, and so an eager client would make requests when it's not ready yet. I implemented a retry logic for the queue consumers (**bot** and **botposter**), that really need it. For **chat**, that only has one job to do there, I prefer to simply ignore the error to keep the container resources free from it - user could try again later.

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

## What's missing?

As of v1.4:

* Adding automated tests

* Handling more complex errors: everything here is in respect of the "happy path".
