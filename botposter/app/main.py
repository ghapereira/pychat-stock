import time

import pika
import requests


RECEIVING_QUEUE = 'stockreceiver'


def main() -> None:
    time.sleep(10)
    credentials = pika.PlainCredentials('admin', 'admin')
    connection_parameters = pika.ConnectionParameters(
        host='rabbitmq',
        credentials=credentials
    )

    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()

    channel.queue_declare(queue=RECEIVING_QUEUE)

    def callback(ch, method, properties, body):
        r = requests.post(
            'http://chat/botchatroom/4c3a3fa4-b66f-4891-93fc-6b0b9b61ef84',
            json={'text': 'Posted by the bot!', 'bot_name': 'stockbot'}
        )

    channel.basic_consume(
        queue=RECEIVING_QUEUE,
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()


if __name__ == '__main__':
    main()
