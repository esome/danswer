import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import cast
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
from danswer.dynamic_configs import get_dynamic_config_store
from danswer.dynamic_configs.interface import ConfigNotFoundError
from danswer.dynamic_configs.interface import JSON_ro
from danswer.utils.logger import setup_logger


logger = setup_logger()

_METADATA_FLAG = "#DANSWER_METADATA="

LOAD_STATE_KEY = "directory_connector_state"
MAX_BATCHES = 10

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
        num_batches = 0

        try:
            state = cast(dict, get_dynamic_config_store().load(LOAD_STATE_KEY))
        except ConfigNotFoundError:
            state = {}

        processed_files: list[str] = []
        documents: list[Document] = []
        done = False
        for file_location in self.file_locations:
            files = _open_files_at_location_recursive(file_location, '')

            for file_name, file in files:
                file_path = os.path.join(file_location, file_name)
                if file_path in state:
                    logger.debug(f"Skipping file '{file_path}' as it has already been processed")
                    continue

                logger.info(f"Batch {num_batches + 1}: Processing file '{file_path}'")
                documents.extend(_process_file(file_name, file))
                processed_files.append(file_path)

                if len(documents) >= self.batch_size:
                    yield documents
                    documents = []

                    for file_path in processed_files:
                        state[file_path] = True

                    num_batches += 1
                    if num_batches >= MAX_BATCHES:
                        logger.info(f"Reached max batches of {MAX_BATCHES}, stopping")
                        done = True
                        break

            if done:
                break

        if documents:
            yield documents

            for file_path in processed_files:
                state[file_path] = True

        get_dynamic_config_store().store(LOAD_STATE_KEY, cast(JSON_ro, state))
