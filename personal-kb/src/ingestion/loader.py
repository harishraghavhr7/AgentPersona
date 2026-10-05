from llama_index.core import SimpleDirectoryReader

from config import DATA_DIR


def load_documents():

    reader = SimpleDirectoryReader(
        input_dir=DATA_DIR,
        recursive=True,
    )

    documents = reader.load_data()

    print(
        f"[Loader] Loaded {len(documents)} documents"
    )

    return documents