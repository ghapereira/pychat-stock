import json
import time

import pika
import requests


RECEIVING_QUEUE = 'publishstock'


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
        incoming = json.loads(body)
        outgoing = {
            'text': f'{incoming["stock_name"]} quote is {incoming["stock_quote"]}',
            'bot_name': incoming['bot_name']
        }

        r = requests.post(
            f'http://chat/v1/botchatroom/{incoming["chatroom"]}',
            json=outgoing
        )

    channel.basic_consume(
        queue=RECEIVING_QUEUE,
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()


if __name__ == '__main__':
    main()
