import base64
import logging
from enum import Enum
from typing import List
from typing import Optional

from pydantic import Field
from pydantic import SecretStr

from common.promptly.blocks.data_extracter.aws_s3_path import AWSS3PathDataExtractorBlock
from common.promptly.blocks.data_extracter.aws_s3_path import AWSS3PathDataExtractorBlockInput
from common.promptly.vectorstore import Document
from common.utils.splitter import CSVTextSplitter
from common.utils.text_extract import extract_text_from_b64_json
from common.utils.splitter import SpacyTextSplitter
from common.utils.utils import validate_parse_data_uri
from datasources.handlers.datasource_type_interface import DataSourceEntryItem
from datasources.handlers.datasource_type_interface import DataSourceSchema
from datasources.handlers.datasource_type_interface import DataSourceTypeInterface
from datasources.handlers.datasource_type_interface import WEAVIATE_SCHEMA
from datasources.models import DataSource
from base.models import Profile

logger = logging.getLogger(__name__)


class MimeType(str, Enum):
    PLAIN_TEXT = 'text/plain'
    CSV = 'text/csv'
    JSON = 'application/json'
    PDF = 'application/pdf'
    RTF = 'application/rtf'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    HTML = 'text/html'
    MP3 = 'audio/mpeg'
    MP4 = 'video/mp4'
    WEBM = 'video/webm'

    def __str__(self):
        return self.value


class S3FileSchema(DataSourceSchema):
    bucket: str = Field(description='S3 bucket name')
    path: str = Field(description='S3 file path')
    mime_type: Optional[MimeType] = Field(
        default=MimeType.PLAIN_TEXT, description='Mime type of the files',
    )
    aws_access_key_id: Optional[str] = Field(
        description='AWS access key ID', default=None,
    )
    aws_secret_access_key: Optional[SecretStr] = Field(
        ...,
        description='AWS secret access key', widget='password',
    )
    region_name: Optional[str] = Field(
        description='AWS region name', default='us-east-1',
    )

    @staticmethod
    def get_content_key() -> str:
        return 'content'

    @staticmethod
    def get_weaviate_schema(class_name: str) -> dict:
        return WEAVIATE_SCHEMA.safe_substitute(
            class_name=class_name,
            content_key=S3FileSchema.get_content_key(),
        )


class S3FileDataSource(DataSourceTypeInterface[S3FileSchema]):
    def __init__(self, datasource: DataSource):
        super().__init__(datasource)
        profile = Profile.objects.get(user=self.datasource.owner)
        self.openai_key = profile.get_vendor_key('openai_key')

    @staticmethod
    def name() -> str:
        return 's3 file'

    @staticmethod
    def slug() -> str:
        return 'S3_file'

    def validate_and_process(self, data: dict) -> List[DataSourceEntryItem]:
        entry = S3FileSchema(**data)
        mime_type = entry.mime_type

        file_name = f'{entry.bucket}/{entry.path}'

        if entry.aws_access_key_id:
            aws_access_key_id = entry.aws_access_key_id
        else:
            aws_access_key_id = self.profile.get_vendor_key(
                'aws_access_key_id',
            )

        if entry.aws_secret_access_key:
            aws_secret_access_key_secret = entry.aws_secret_access_key.get_secret_value(
            ) if entry.aws_secret_access_key else None
        else:
            aws_secret_access_key_secret = self.profile.get_vendor_key(
                'aws_secret_access_key',
            )

        if entry.region_name:
            region_name = entry.region_name
        else:
            region_name = self.profile.get_vendor_key('aws_default_region')

        s3_file_data_extractor = AWSS3PathDataExtractorBlock(
            configuration={'aws_access_key_id': aws_access_key_id,
                           'aws_secret_access_key': aws_secret_access_key_secret, 'region_name': region_name},
        )

        result = s3_file_data_extractor.process(
            AWSS3PathDataExtractorBlockInput(
                path=entry.path, bucket=entry.bucket).dict(),
        )

        if result.result.metadata.http_status_code != 200:
            logger.error(
                f'Error fetching file from S3: {result.result.metadata.http_status}',
            )
            raise Exception('Error fetching file from S3')

        mime_type = result.result.metadata.content_type
        base64_encoded_file_content = base64.b64encode(
            result.result.content,
        ).decode()

        data_url = 'data:{};name={};base64,{}'.format(
            mime_type, file_name, base64_encoded_file_content,
        )

        mime_type, file_name, file_data = validate_parse_data_uri(data_url)

        data_source_entry = DataSourceEntryItem(
            name=file_name, data={'mime_type': mime_type,
                                  'file_name': file_name, 'file_data': file_data},
        )

        return [data_source_entry]

    def get_data_documents(self, data: dict) -> Optional[DataSourceEntryItem]:
        logger.info(
            f"Processing file: {data.data['file_name']} mime_type: {data.data['mime_type']}",
        )

        file_text = extract_text_from_b64_json(
            data.data['mime_type'],
            data.data['file_data'], openai_key=self.openai_key, file_name=data.data['file_name'],
        )

        if data.data['mime_type'] == 'text/csv':
            docs = [
                Document(page_content_key=self.get_content_key(), page_content=t, metadata={'source': data.data['file_name']}) for t in CSVTextSplitter(
                    chunk_size=2, length_function=CSVTextSplitter.num_tokens_from_string_using_tiktoken,
                ).split_text(file_text)
            ]
        else:
            docs = [
                Document(page_content_key=self.get_content_key(), page_content=t, metadata={'source': data.data['file_name']}) for t in SpacyTextSplitter(
                    chunk_size=1500,
                ).split_text(file_text)
            ]
        return docs

    def similarity_search(self, query: str, *args, **kwargs) -> List[dict]:
        return super().similarity_search(query, *args, **kwargs)