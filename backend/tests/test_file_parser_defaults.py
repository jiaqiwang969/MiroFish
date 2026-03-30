from app.utils.file_parser import split_text_into_chunks


def test_split_text_into_chunks_uses_6500_character_default_chunk_size():
    text = "a" * 6400

    chunks = split_text_into_chunks(text)

    assert chunks == [text]
