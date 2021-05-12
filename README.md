# pychat-stock

A simple chat application assignment

## Objective

This is an application that has the following requirements:

* Allow registered users to log in and talk with other users in a chatroom

* Allow users to post messages as commands into the chatroom with the format `/stock=stock_code`, which will be parsed by a decoupled bot that will call an API for obtaining the stock value

* Have the chat messages ordered by their timestamps, showing only the last 50 messages

## Running

The project is organized as a [Docker Compose](https://docs.docker.com/compose/) environment that will run the application Docker containers (chat and bot), and the backend dependencies (Redis and RabbitMQ). The machine that will run the project should have Docker and Docker Compose installed (the machine I used for development has Docker 20.10 and Docker-Compose 1.27). To run the project just run `docker-compose up -d`, and to deactivate after it `docker-compose down`. If you want to take a look at the logs as they progress, run `docker-compose up`, and press Ctrl+C to destroy the cluster -- pressing again will probably be needed since some open connections may leave the system hanging.

This project was developed under an Ubuntu 20.04 machine.

![Running docker-compose](https://github.com/ghapereira/pychat-stock/blob/main/static/docker-compose.gif)

### Executing the client

![Base usage](https://github.com/ghapereira/pychat-stock/blob/main/static/baseusage.gif)

To execute the client, open the HTML file `pychat-stock/static/login.html` in a web browser. There, the page contains four sections:

* At the top, a session containing name and password fields, and a send button. This is the login session. Before doing anything else, please make a login. If you are using the default-provided file `db.sql`, there are two user/password combinations: user `plutothedog`, with password `1234`, and `john`, with password `doe`.

* The second session contains the available chatrooms. When logging in, the application will send a GET request to the `/v1/chatroom` endpoint and fill in a list of available chatrooms. If using the default db, there will be two available chatrooms with some conversations on it. The user must single-click on any of them to
set the value of the chatroom to the next section.

* The third section contains the chatroom conversations. After clicking on an available one on the past section it will be put into the "chatroom" text field and updated with the conversations. There is a "Refresh" button near to it because the server is NOT communicating with the front actively with, for example, websockets, so it falls on the client to periodically refresh the conversations itself.

* On the fourth and last section an user can type a message and send it to the chatroom. After posting the message the client will refresh the messages. If other messages were posted in the meantime by, say, other users or the bot they will be visible there.

### Creating more items

If you don't want to use the basic provided database, or if you want to create other items, there are endpoints for creation of chatrooms, users and messages. They are better described in the Postman collection or in the Swagger documentation that is available on the FastAPI server when it's running on [http://127.0.0.1:8000/docs#/](http://127.0.0.1:8000/docs#/). `Create user` and `Create chatroom` are available without authentication, so in tests user/chatroom creation is fast. If you create a chatroom being already logged in, you can refresh the page and login again to see the new ones, but you can also hit the "login" button again and it will have the same effect.

If you want to simply drop the provided database file and restart the server, that's ok: the [sqlalchemy](https://www.sqlalchemy.org/) ORM system will create a new schema, and no prior information is needed for the system to work -- of course, no logins and messages are thus possible before creating chatrooms and users!

## Architecture

The architecture was designed to meet the given requirements. There are five listed Docker containers in the `docker-compose.yml` definition file:

* **chat**: Is the main container that serves the application. Based on the FastAPI container, it serves on the port 8000 of localhost. All client communications must happen against it.

* **bot**: From a base Python container, this one listens to the _requeststock_ queue on the **rabbitmq** container for stock requests; when one comes it fetch stock data from an external API, parses this data and then posts this result back to the _publishstock_ queue, for publishing to the appropriate chatroom.

* **botposter**: Reads from the _publishstock_ queue and posts a message to the correspondent chatroom at **chat**. This function could theoretically be done by **chat** itself, but I found that leaving a dedicated container to be listening from the queue would free responsibilities and avoid potetial blocks from it.

* **redis**: Redis cache. Used for storing login tokens, so users may be logged off after a period of inactivity - they need to refresh a token periodically, or login again.

* **rabbitmq**: RabbitMQ container, in this case used to provide AMQP queues. It is used to decouple the main server from the bot, as requested.

Other than the containers the other components that are present are a sqlite database, used for persisting information, and the static files of the frontend.

### Flows

This section details the architecture of the functionality flows.

#### Login

![Login flow](https://github.com/ghapereira/pychat-stock/blob/main/static/login_flow.png)

For login, the client need to send a POST request with username and password for the `/v1/login` endpoint:

```json
{
	"username": "plutothedog",
	"password": "1234"
}
```

A successful response is as follows:

```json
{
    "token": "f473ee87-d28e-4607-8641-3f9f0595e833",
    "session_id": "51c541e3-571b-48dd-a172-1b2096f0d455",
    "expires_in": "2021-05-11T00:59:14"
}
```

The implemented client saves these informations on local variables for simplicity. A better idea would be store them on cookies or localstorage. On the backend, the password is retrieved from the database and checked against the provided value, generating a token and storing it in the Redis cache, for 5 minutes as default. After this a new login must be done. I even drafted a login auto-refresh on each interaction with the server, but abandoned the idea for now. Step 3 ("store login") isn't actually implemented, although the database table for this functionality is there.

#### Message

![Message flow](https://github.com/ghapereira/pychat-stock/blob/main/static/message_flow.png)

For a message containing a text that does not begin with `/stock=` the flow is to first verify whether the user is logged in and, if so, save the message to the database and return a confirmation of success:

`POST /v1/chatroom/{chatroomid}`
```json
{
	"text": "A message to the chatroom"
}
```

RESPONSE
```json
{
    "msg": "message posted"
}
```

On the implemented client this action also triggers a GET request for `/v1/chatroom/{chatroomId}`, that reads the messages in the chatroom and display them on the page.

#### Stock message

![Stock message flow](https://github.com/ghapereira/pychat-stock/blob/main/static/message_bot_flow.png)

This flow is similar to message on its start, with the sole difference that if the message text starts with `/stock=something`, the string `something` will be interpreted as a stock to be checked for. **chat** will send a message to the queue and answer to the user that the message was posted. From the queue, **bot** will read and ask for the stock on the external API. Here I wanted to keep the stock on cache for a bit, but decided not to do it for now. After this the message is posted back to a different queue and read from **botposter**. This one will simply post the message back to **chat** in an unprotected endpoint, and this one is saved on the database and available to be read on the front-end. Due to these components taking a bit of time to execute, you may want to wait a few seconds before refreshing the messages.

### Architectural considerations

* The decision for passing the headers for both username (that should be user id - see in **Security considerations**) and session id are due to allow for a same user to be concurrently logged in in multiple environments.

* There are some opportunities for parallelism. The **chat** service is not tightly attached to anything but the database. If an external database was to be used, not even this. So multiple autoscaled **chat** services could exist. Web caches could be used to serve front-end and allow for this autoscaling to be transparent under it. The queues could be used to throttle requests on a high usage scenario.

* The **botposter** service exists with the sole purpose of POSTing back messages from the queue to the main **chat** service. I would prefer doing it directly from the queue, rather than having an intermediate doing it, but I don't know about any such solution. In a cloud environment, however, there would be no need for this: a simple serverless function (AWS Lambda, Azure Functions, GCP Cloud Functions) would do the trick in an scalable way. Of course, if usage would be extreme this could incur in a high cost, but the possibility is at least worth investigating.

* In the Docker Compose it is used a dependency feature so the containers that use the queue will not start before it. Starting, however, isn't the same as _being ready_. In this way, it's possible that the containers that use the queue are ready before the queue, and so an eager client would make requests when it's not ready yet. I implemented a retry logic for the queue consumers (**bot** and **botposter**), that really need it. For **chat**, that only has one job to do there, I prefer to simply ignore the error to keep the container resources free from it - user could try again later.

## Test collection

There is a Postman collection present on the **postman** directory. There, one can import the **PyChat Stock v1.postman_collection.json** file on Postman, and the local and global variables, respectively, from **LOCAL.postman_environment.json** and **My Workspace.postman_globals.json**. After selecting the corresponding environments, this collection can be used for quickly testing the application, via creating chatrooms and users and then logging in, posting messages and reading from the chatrooms.

## Security considerations

As a simple project with a strict time frame, many security issues are present. Some of them are listed in the following topics:

* The worst offense of the whole project is that it DOES NOT use HTTPS. This is egregious. As requests will be trafficking in plaintext, it is trivial to obtain passwords and confidential information from this system. If any security measure would need to be taken here this is certainly the priority.

* Running a custom-made login flow while having available solutions as Oauth, for example, is unnecessary, unsafe and not a smart decision. The login flow here is used only to illustrate a feasible system, nothing else. Cloud providers IAM systems also are better employed for this.

* For token validation during the various flows the system passes username and token all the time. This is really bad; user uuid should be used instead, so the username would be used only once, for login, and then an internal system information would be used, so an attacker wouldn't have so easily available an username.

* Some endpoints such as user creation and chatroom creation, among others, are left free for use unauthenticated. This is done for simplicity, but it is obvious that such actions SHOULD NOT be left this way.

* The database is stored unencrypted and without a password for accessing it. User password is left hashed (and salted), and this is probably the only somewhat serious protection on the whole system, but as stated above password travels unencrypted on the network for login, so it's not a strong protection.

* On some instances database records ids travel in the network among requests. One should NEVER use database records ids as keys outside it, since this leaves open internal details for attackers.

* For the simplicity of the front-end, allowing it to run from localhost against the server, it ignores CORS. This is a BAD practice also.

## What's missing?

As of v1.4:

* On the chatroom it's not _explicit_ that the messages have different owners. They can be checked for the ownership in the database (for this, the tool I used for this project is [DB Browser for SQLite](https://sqlitebrowser.org/)), but there will be no visual clues regarding this on the application.

* Adding automated tests. Since the code is fairly simple, unit tests would be at best scarce, with more emphasis being given to integration tests using mocks. However, due to time constraints this was not implemented. One can notice in the file `chat/app/repository.py` for example that all methods receive `db`, which is the database session, as a parameter. This is a good case for inserting a mock. The other files are more or less prepared in this scenario, but since there were not a strong case for testing e.g. business logic I left it out. Additional features such as chatroom ownership/allowed users would be a better case for testing this.

* Handling more complex errors: everything here is in respect of the "happy path". This includes not handling malformations on the `/stock` command.
