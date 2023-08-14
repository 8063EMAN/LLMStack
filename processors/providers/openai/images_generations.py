import logging
from typing import List
from typing import Optional

from asgiref.sync import async_to_sync
from pydantic import conint
from pydantic import Field

from common.promptly.blocks.vendor.openai import OpenAIAPIProcessorOutput
from common.promptly.blocks.vendor.openai import OpenAIAPIProcessorOutputMetadata
from common.promptly.blocks.vendor.openai import OpenAIImageGenerationsProcessor
from common.promptly.blocks.vendor.openai import OpenAIImageGenerationsProcessorConfiguration
from common.promptly.blocks.vendor.openai import OpenAIImageGenerationsProcessorInput
from common.promptly.blocks.vendor.openai import OpenAIImageGenerationsProcessorOutput
from common.promptly.blocks.vendor.openai import Size
from common.utils.utils import get_key_or_raise
from processors.providers.api_processor_interface import ApiProcessorInterface
from processors.providers.api_processor_interface import BaseSchema
from processors.providers.api_processor_interface import IMAGE_WIDGET_NAME

logger = logging.getLogger(__name__)


class ImagesGenerationsInput(BaseSchema):
    prompt: str = Field(
        ...,
        description='A text description of the desired image(s). The maximum length is 1000 characters.',
        example='A cute baby sea otter',
    )


class ImagesGenerationsOutput(OpenAIAPIProcessorOutput, BaseSchema):
    metadata: Optional[OpenAIAPIProcessorOutputMetadata] = Field(
        widget='hidden',
    )
    data: List[str] = Field(
        default=[], description='The generated images.', widget=IMAGE_WIDGET_NAME,
    )


class ImagesGenerationsConfiguration(OpenAIImageGenerationsProcessorConfiguration, BaseSchema):
    size: Optional[Size] = Field(
        '1024x1024',
        description='The size of the generated images. Must be one of `256x256`, `512x512`, or `1024x1024`.',
        example='1024x1024',
        advanced_parameter=False,
    )
    n: Optional[conint(ge=1, le=4)] = Field(
        1,
        description='The number of images to generate. Must be between 1 and 10.',
        example=1,
        advanced_parameter=False,
    )


class ImagesGenerations(ApiProcessorInterface[ImagesGenerationsInput, ImagesGenerationsOutput, ImagesGenerationsConfiguration]):

    """
    OpenAI Images Generations API
    """
    def name() -> str:
        return 'open ai/image generations'

    def slug() -> str:
        return 'openai_image_generations'

    def process(self) -> dict:
        _env = self._env
        prompt = self._input.prompt

        if not prompt:
            raise Exception('No prompt found in input')

        image_generations_api_processor_input = OpenAIImageGenerationsProcessorInput(
            env=_env, prompt=prompt,
        )

        response: OpenAIImageGenerationsProcessorOutput = OpenAIImageGenerationsProcessor(
            configuration=self._config.dict(),
        ).process(image_generations_api_processor_input.dict())

        async_to_sync(self._output_stream.write)(
            ImagesGenerationsOutput(
            data=response.answer, metadata=response.metadata,
            ),
        )

        output = self._output_stream.finalize()

        return output