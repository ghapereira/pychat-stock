import time

import pika


SENDING_QUEUE = 'stockreceiver'

def main() -> None:
    time.sleep(15)

    credentials = pika.PlainCredentials('admin', 'admin')
    connection_parameters = pika.ConnectionParameters(
        host='rabbitmq',
        credentials=credentials
    )
    connection = pika.BlockingConnection(connection_parameters)

    channel = connection.channel()

    channel.queue_declare(queue=SENDING_QUEUE)

    channel.basic_publish(
        exchange='',
        routing_key=SENDING_QUEUE,
        body='Test 1'
    )

    time.sleep(15)

    print('Sent message')

    channel.basic_publish(
        exchange='',
        routing_key=SENDING_QUEUE,
        body='Test 2'
    )

    time.sleep(15)

    print('Sent message')

    channel.basic_publish(
        exchange='',
        routing_key=SENDING_QUEUE,
        body='Test 3'
    )

    connection.close()

if __name__ == '__main__':
    main()
