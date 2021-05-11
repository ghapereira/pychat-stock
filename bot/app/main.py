import io
import json
import time

import pandas as pd
import pika
import requests


RECEIVING_QUEUE = 'requeststock'
SENDING_QUEUE = 'publishstock'
QUEUE_RECONNECT_DELAY_SECONDS = 10

STOCK_API_URL = 'https://stooq.com/q/l/?s={stock}&f=sd2t2ohlcv&h&e=csv'


def main() -> None:
    while True:
        try:
            queue_listen()
        except pika.exceptions.AMQPConnectionError:
            print(f'Could not connect to queue, retrying in {QUEUE_RECONNECT_DELAY_SECONDS} seconds')
            time.sleep(QUEUE_RECONNECT_DELAY_SECONDS)


def queue_listen() -> None:
    credentials = pika.PlainCredentials('admin', 'admin')
    connection_parameters = pika.ConnectionParameters(
        host='rabbitmq',
        credentials=credentials
    )
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()

    channel.queue_declare(queue=RECEIVING_QUEUE)
    channel.queue_declare(queue=SENDING_QUEUE)

    def callback(ch, method, properties, body):
        incoming_message = json.loads(body)

        r = requests.get(get_stock_url(incoming_message['stock_code']))
        stock_data = pd.read_csv(io.StringIO(r.text))
        stock_name = stock_data['Symbol'][0]
        stock_quote = stock_data['Close'][0]

        stock_response = {
            'stock_name': stock_name,
            'stock_quote': stock_quote,
            'chatroom': incoming_message['chatroom'],
            'bot_name': incoming_message['bot_name']
        }

        channel.basic_publish(
            exchange='',
            routing_key=SENDING_QUEUE,
            body=json.dumps(stock_response)
        )

    channel.basic_consume(
        queue=RECEIVING_QUEUE,
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()


def get_stock_url(stock_name: str) -> str:
    return STOCK_API_URL.format(stock=stock_name)


if __name__ == '__main__':
    main()
