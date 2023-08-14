import logging
from typing import List
from typing import Optional

from pydantic import Field

from common.promptly.vectorstore import Document
from common.utils.text_extract import extract_text_from_b64_json
from common.utils.splitter import SpacyTextSplitter
from common.utils.utils import validate_parse_data_uri
from datasources.handlers.datasource_type_interface import DataSourceEntryItem
from datasources.handlers.datasource_type_interface import DataSourceSchema
from datasources.handlers.datasource_type_interface import DataSourceTypeInterface
from datasources.handlers.datasource_type_interface import WEAVIATE_SCHEMA


logger = logging.getLogger(__name__)


class TxtFileSchema(DataSourceSchema):
    file: str = Field(
        ..., widget='file',
        description='File to be processed', accepts={
            'application/rtf': [],
            'text/plain': [],
        }, maxSize=20000000,
    )

    @staticmethod
    def get_content_key() -> str:
        return 'content'

    @staticmethod
    def get_weaviate_schema(class_name: str) -> dict:
        return WEAVIATE_SCHEMA.safe_substitute(
            class_name=class_name,
            content_key=TxtFileSchema.get_content_key(),
        )


class TxtFileDataSource(DataSourceTypeInterface[TxtFileSchema]):

    @staticmethod
    def name() -> str:
        return 'txt_file'

    @staticmethod
    def slug() -> str:
        return 'txt_file'

    def validate_and_process(self, data: dict) -> List[DataSourceEntryItem]:
        entry = TxtFileSchema(**data)
        mime_type, file_name, file_data = validate_parse_data_uri(entry.file)
        if mime_type not in ['application/rtf', 'text/plain']:
            raise ValueError(
                f'Invalid mime type: {mime_type}, expected: application/rtf or text/plain',
            )

        data_source_entry = DataSourceEntryItem(
            name=file_name, data={'mime_type': mime_type, 'file_name': file_name, 'file_data': file_data},
        )

        return [data_source_entry]

    def get_data_documents(self, data: DataSourceEntryItem) -> Optional[DataSourceEntryItem]:
        logger.info(
            f"Processing file: {data.data['file_name']} mime_type: {data.data['mime_type']}",
        )

        file_text = extract_text_from_b64_json(
            mime_type=data.data['mime_type'],
            base64_encoded_data=data.data['file_data'],
            file_name=data.data['file_name'],
        )

        docs = [
            Document(page_content_key=self.get_content_key(), page_content=t, metadata={'source': data.data['file_name']}) for t in SpacyTextSplitter(
                chunk_size=1500,
            ).split_text(file_text)
        ]

        return docs

    def similarity_search(self, query: str, *args, **kwargs) -> List[dict]:
        return super().similarity_search(query, *args, **kwargs)