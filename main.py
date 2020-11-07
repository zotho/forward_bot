import json
import logging
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest

logging.basicConfig(format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.INFO)
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


with TelegramClient("forward_bot", api_id, api_hash) as client:
    @client.on(events.NewMessage(incoming=True))
    async def channel_handler(event):
        logger.info(event)
        if event.is_channel:
            await event.message.forward_to(target_username)

    @client.on(events.NewMessage(chats=[target_username], incoming=True))
    async def add_subscription_handler(event):
        logger.info(event)
        if event.fwd_from and event.fwd_from.channel_id:
            new_channel_id = event.fwd_from.channel_id
            try:
                await client(JoinChannelRequest(new_channel_id))
            except ChannelPrivateError as exception:
                logger.warning(f"Channel is private: {new_channel_id}. Error: {exception}")
            await event.reply(f"Added {new_channel_id}")

    @client.on(events.NewMessage(chats=[target_username], incoming=True, pattern="Stop"))
    async def stop_subscription_handler(event):
        logger.info(event)
        if event.message.is_reply and event.message.reply_to_msg_id:
            message = await client.get_messages(target_username, ids=event.message.reply_to_msg_id)
            if message and message.fwd_from and message.fwd_from.channel_id:
                delete_channel_id = message.fwd_from.channel_id
                await client(LeaveChannelRequest(delete_channel_id))
                await event.reply(f"Stopped {delete_channel_id}")
            else:
                await event.reply("Can't find channel id")

    client.run_until_disconnected()
