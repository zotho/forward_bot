import json
import logging
import os
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.DEBUG if bool(os.getenv("DEBUG")) else logging.INFO,
)
logger = logging.getLogger(__name__)

config_path = Path("config.json")
if not config_path.exists():
    raise FileNotFoundError(
        "Please create config.json file with api_id, api_hash, target_username fields"
    )

config = json.loads(config_path.read_text())

api_id = config["api_id"]
api_hash = config["api_hash"]
target_username = config["target_username"]


def get_forwarded_channel_id(event):
    return event.fwd_from and event.fwd_from.from_id.to_dict().get("channel_id")


with TelegramClient("forward_bot", api_id, api_hash) as client:
    @client.on(events.NewMessage(
        incoming=True,
        func=lambda e: e.is_channel and e.message and e.message.grouped_id is None
    ))
    async def channel_handler(event):
        logger.info("channel_handler")
        try:
            await event.message.forward_to(target_username)
        except Exception as error:
            logger.error(event.to_json())
            raise error

    @client.on(events.Album(func=lambda e: e.is_channel))
    async def channel_album_handler(event):
        logger.info("channel_album_handler")
        try:
            await event.forward_to(target_username)
        except Exception as error:
            logger.error(event.to_json())
            raise error

    @client.on(events.NewMessage(
        chats=[target_username], incoming=True,
        func=get_forwarded_channel_id
    ))
    async def add_subscription_handler(event):
        logger.info("add_subscription_handler")
        channel_id = get_forwarded_channel_id(event)
        if channel_id:
            try:
                response = await client(JoinChannelRequest(channel_id))
                channel_title = response.chats[0].title
                await event.reply(f"Added: {channel_title} ({channel_id})")
            except ChannelPrivateError as exception:
                logger.warning(f"Channel is private: {channel_id}. Error: {exception}")
                await event.reply(f"Channel is private {channel_id}")
        else:
            await event.reply("Can't find channel id")

    @client.on(events.NewMessage(
        chats=[target_username], incoming=True, pattern="Stop",
        func=lambda e: e.message.is_reply and e.message.reply_to_msg_id
    ))
    async def stop_subscription_handler(event):
        logger.info("stop_subscription_handler")
        message = await client.get_messages(target_username, ids=event.message.reply_to_msg_id)
        channel_id = message and get_forwarded_channel_id(message)
        if channel_id:
            response = await client(LeaveChannelRequest(channel_id))
            channel_title = response.chats[0].title
            await event.reply(f"Stopped: {channel_title} ({channel_id})")
        else:
            await event.reply("Can't find channel id")

    client.run_until_disconnected()
