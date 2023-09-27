import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from typing import IO

from danswer.configs.app_configs import INDEX_BATCH_SIZE
from danswer.configs.app_configs import DIRECTORY_CONNECTOR_PATH
from danswer.configs.constants import DocumentSource
from danswer.connectors.file.utils import get_file_ext
from danswer.connectors.interfaces import GenerateDocumentsOutput
from danswer.connectors.interfaces import LoadConnector
from danswer.connectors.models import Document
from danswer.connectors.models import Section
from danswer.utils.logger import setup_logger


logger = setup_logger()

_METADATA_FLAG = "#DANSWER_METADATA="


def _open_files_at_location_recursive(
    base_path: str | Path,
    file_path: str | Path,
) -> Generator[tuple[str, IO[Any]], Any, None]:
    for file in os.listdir(os.path.join(base_path, file_path)):
        rel_file_path = os.path.join(file_path, file)
        abs_file_path = os.path.join(base_path, rel_file_path)
        if os.path.isdir(abs_file_path):
            yield from _open_files_at_location_recursive(base_path, rel_file_path)
        else:
            extension = get_file_ext(abs_file_path)
            if extension == ".txt":
                with open(abs_file_path, "r", encoding = "utf8") as file:
                    yield str(rel_file_path), file
            else:
                logger.warning(f"Skipping file '{abs_file_path}' with extension '{extension}'")

def _process_file(file_name: str, file: IO[Any]) -> list[Document]:
    metadata = {}
    file_content_raw = ""
    for ind, line in enumerate(file):
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        line = str(line)

        if ind == 0 and line.startswith(_METADATA_FLAG):
            metadata = json.loads(line.replace(_METADATA_FLAG, "", 1).strip())
        else:
            file_content_raw += line

    return [
        Document(
            id=file_name,
            sections=[Section(link=metadata.get("link", ""), text=file_content_raw)],
            source=DocumentSource.FILE,
            semantic_identifier=file_name,
            metadata={},
        )
    ]


class LocalDirectoryConnector(LoadConnector):
    def __init__(self) -> None:
        self.file_locations = [Path(DIRECTORY_CONNECTOR_PATH)]
        self.batch_size = INDEX_BATCH_SIZE

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        pass

    def load_from_state(self) -> GenerateDocumentsOutput:
        documents: list[Document] = []
        for file_location in self.file_locations:
            files = _open_files_at_location_recursive(file_location, '')

            for file_name, file in files:
                documents.extend(_process_file(file_name, file))

                if len(documents) >= self.batch_size:
                    yield documents
                    documents = []

        if documents:
            yield documents
