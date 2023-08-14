import logging
import time
from typing import Dict
from typing import List
from typing import Optional

from asgiref.sync import async_to_sync
from pydantic import Field

from common.promptly.blocks.http import BearerTokenAuth
from common.promptly.blocks.http import HttpAPIProcessor
from common.promptly.blocks.http import HttpAPIProcessorInput
from common.promptly.blocks.http import HttpMethod
from common.promptly.blocks.http import JsonBody
from play.actor import BookKeepingData
from processors.providers.api_processor_interface import ApiProcessorInterface
from processors.providers.api_processor_interface import BaseSchema


logger = logging.getLogger(__name__)


class DiscordEmbed(BaseSchema):
    title: str
    description: str
    color: Optional[int]


class DiscordSendMessageInput(BaseSchema):
    discord_user_id: str
    discord_username: str
    discord_global_name: str
    app_id: str
    token: str
    bot_token: str
    channel_id: str
    text: str
    embeds: Optional[List[DiscordEmbed]]


class DiscordSendMessageOutput(BaseSchema):
    code: int


class DiscordSendMessageConfiguration(BaseSchema):
    pass


class DiscordSendMessageProcessor(
    ApiProcessorInterface[
        DiscordSendMessageInput, DiscordSendMessageOutput, DiscordSendMessageConfiguration,
    ],
):
    """
    Discord Send Message API
    """

    def name() -> str:
        return 'discord/send_message'

    def slug() -> str:
        return 'discord_send_message'

    def process(self) -> dict:
        _env = self._env
        input = self._input.dict()
        url = f"https://discord.com/api/v10/webhooks/{input['app_id']}/{input['token']}"

        http_processor = HttpAPIProcessor(configuration={'timeout': 60})
        response = http_processor.process(
            HttpAPIProcessorInput(
                url=url,
                method=HttpMethod.POST,
                headers={'Content-Type': 'application/json'},
                authorization=BearerTokenAuth(token=input['token']),
                body=JsonBody(
                    json_body={
                        'content': input['text'],
                    },
                ),
            ).dict(),
        )

        async_to_sync(self._output_stream.write)(
            DiscordSendMessageOutput(code=200),
        )

        return self._output_stream.finalize()

    def get_bookkeeping_data(self) -> BookKeepingData:
        return BookKeepingData(input=self._input, timestamp=time.time(), run_data={'discord': {'user': self._input.discord_user_id, 'username': self._input.discord_username, 'global_name': self._input.discord_global_name}})