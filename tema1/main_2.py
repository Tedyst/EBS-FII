import argparse
import asyncio
import signal
import multiprocessing

from common import AppState
from workers.aggregator import start_aggregation_worker
from workers.filter import start_filter_worker
from workers.create_pubs import create_publications
from workers.clear import clear_all
from workers.consumer import consumer_loop


def process_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        type=str,
        help="RabbitMQ host to connect to",
        default="localhost",
    )
    parser.add_argument(
        "--username",
        type=str,
        help="RabbitMQ username to use",
        default="user",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="RabbitMQ password to use",
        default="password",
    )
    parser.add_argument(
        "--processes",
        type=int,
        help="Number of processes to use",
        default=1,
    )

    subparsers = parser.add_subparsers(dest="command")
    consumer_parser = subparsers.add_parser(
        "consumer", help="Start the consumer worker"
    )
    consumer_parser.add_argument(
        "count",
        type=int,
        help="Number of subscriptions to create",
        default=10,
    )

    filter_parser = subparsers.add_parser(
        "filter", help="Start the filter worker with specified fields"
    )
    filter_parser.add_argument(
        "fields",
        type=str,
        nargs="+",
        help="List of fields to filter by (use 'all' for all fields)",
    )
    filter_parser.set_defaults(fields=["all"])

    create_pubs = subparsers.add_parser("create_pubs", help="Create subscriptions")
    create_pubs.add_argument(
        "count",
        type=int,
        help="Number of publications to create",
        default=10,
    )

    subparsers.add_parser("clear", help="Clear all streams and queues")

    aggregate_parser = subparsers.add_parser(
        "aggregate", help="Start the aggregation worker with specified fields"
    )
    aggregate_parser.add_argument(
        "fields",
        type=str,
        nargs="+",
        help="List of fields to use for aggregation",
    )

    args = parser.parse_args()

    return parser, args


async def main(args: dict):
    appstate = AppState(
        host=args["host"],
        username=args["username"],
        password=args["password"],
    )

    if args["command"] == "filter":
        await start_filter_worker(appstate, args["fields"])
    elif args["command"] == "create_pubs":
        await create_publications(appstate, args["count"])
    elif args["command"] == "clear":
        await clear_all(appstate)
    elif args["command"] == "aggregate":
        await start_aggregation_worker(appstate, args["fields"])
    elif args["command"] == "consumer":
        await consumer_loop(
            appstate,
            args["count"],
        )
    elif args["command"] == "filter":
        await start_filter_worker(
            appstate,
            args["fields"],
        )


def _main(args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = asyncio.ensure_future(main(args))
    loop.add_signal_handler(signal.SIGINT, lambda: main_task.cancel())
    loop.run_until_complete(main_task)


if __name__ == "__main__":
    parser, args = process_arguments()

    if args.command is None:
        parser.print_help()
        exit(1)

    args_dict = args.__dict__

    if args.processes == 1:
        _main(args_dict)
    else:
        with multiprocessing.Pool(processes=args.processes) as pool:
            for i in range(args.processes):
                print(f"Starting process {i}")
                pool.apply_async(
                    _main,
                    (args_dict,),
                )
            pool.close()
            pool.join()
