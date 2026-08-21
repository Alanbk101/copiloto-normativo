"""
Tests for src.embeddings.encoder.

The real model (~2 GB) is never loaded in the test suite.  Instead, we
patch the module-level singleton so _get_model() returns a MagicMock whose
encode() method returns a pre-shaped numpy array.

What we verify:
  - encode_passages applies the required "passage: " prefix to every text.
  - The returned vectors have exactly EMBEDDING_DIM elements.
  - encode_query applies the "query: " prefix and returns a flat vector.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from src.embeddings.encoder import _EMBEDDING_DIM, encode_passages, encode_query


@pytest.fixture(autouse=True)
def mock_model():
    """Replace the module-level singleton with a MagicMock for every test."""
    model = MagicMock()
    with patch("src.embeddings.encoder._model", model):
        yield model


def test_encode_passages_applies_passage_prefix(mock_model: MagicMock) -> None:
    mock_model.encode.return_value = np.zeros((2, _EMBEDDING_DIM))

    encode_passages(["primer texto", "segundo texto"])

    mock_model.encode.assert_called_once_with(
        ["passage: primer texto", "passage: segundo texto"],
        convert_to_numpy=True,
    )


def test_encode_passages_returns_correct_dimension(mock_model: MagicMock) -> None:
    n = 3
    mock_model.encode.return_value = np.zeros((n, _EMBEDDING_DIM))

    result = encode_passages(["a", "b", "c"])

    assert len(result) == n
    assert all(len(vec) == _EMBEDDING_DIM for vec in result)


def test_encode_passages_returns_list_of_lists(mock_model: MagicMock) -> None:
    mock_model.encode.return_value = np.zeros((1, _EMBEDDING_DIM))

    result = encode_passages(["texto"])

    assert isinstance(result, list)
    assert isinstance(result[0], list)
    assert isinstance(result[0][0], float)


def test_encode_query_applies_query_prefix(mock_model: MagicMock) -> None:
    mock_model.encode.return_value = np.zeros(_EMBEDDING_DIM)

    encode_query("¿cuál es el plazo máximo?")

    mock_model.encode.assert_called_once_with(
        "query: ¿cuál es el plazo máximo?",
        convert_to_numpy=True,
    )


def test_encode_query_returns_correct_dimension(mock_model: MagicMock) -> None:
    mock_model.encode.return_value = np.zeros(_EMBEDDING_DIM)

    result = encode_query("consulta de prueba")

    assert len(result) == _EMBEDDING_DIM
    assert isinstance(result, list)
    assert isinstance(result[0], float)
