from types import SimpleNamespace

from scripts.knowledge import (
    book_filter,
    build_points,
    chunk_text,
    scan_book_index,
    search_filter,
    stable_book_id,
    stable_point_id,
)


def test_stable_book_id_normalizes_title_category_and_collection():
    first = stable_book_id("valtyk_knowledge", "  Life Force  ", "Salud")
    second = stable_book_id("valtyk_knowledge", "life force", "salud")
    third = stable_book_id("otra", "life force", "salud")

    assert first == second
    assert first != third
    assert len(first) == 28


def test_stable_point_id_uses_chunk_index_and_content():
    first = stable_point_id("valtyk_knowledge", "Libro", "Categoria", 0, "texto base")
    second = stable_point_id("valtyk_knowledge", "Libro", "Categoria", 1, "texto base")
    third = stable_point_id("valtyk_knowledge", "Libro", "Categoria", 0, "texto base ampliado")

    assert first != second
    assert first != third
    assert len(first) == 36


def test_filters_match_existing_qdrant_payload_shape():
    expected = {
        "must": [
            {"key": "metadata.book_title", "match": {"value": "Libro"}},
            {"key": "metadata.category", "match": {"value": "Psicologia"}},
        ]
    }
    assert book_filter("Libro", "Psicologia") == expected
    assert sorted(search_filter("Psicologia", "Libro")["must"], key=lambda item: item["key"]) == sorted(
        expected["must"],
        key=lambda item: item["key"],
    )
    assert search_filter() is None


def test_chunk_text_keeps_overlap_and_splits_long_content():
    text = " ".join([f"frase {index}." for index in range(260)])
    chunks = chunk_text(text, chunk_size=520, overlap=80)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert len(chunks[0]) <= 520


def test_build_points_preserves_global_chunk_index_across_batches():
    chunks = ["primer fragmento", "segundo fragmento"]
    vectors = [[0.1, 0.2], [0.3, 0.4]]
    points = build_points(
        collection="valtyk_knowledge",
        title="Libro",
        category="General",
        chunks=chunks,
        vectors=vectors,
        source="libro.pdf",
        start_index=64,
    )

    assert points[0]["payload"]["metadata"]["chunk_index"] == 64
    assert points[1]["payload"]["metadata"]["chunk_index"] == 65
    assert points[0]["payload"]["metadata"]["book_title"] == "Libro"
    assert points[0]["payload"]["content"] == "primer fragmento"


class FakeQdrantClient:
    def __init__(self):
        self.config = SimpleNamespace(collection="valtyk_knowledge")
        self.calls = 0

    def scroll(self, *, limit, offset=None, with_payload=True, payload_filter=None):
        self.calls += 1
        if offset is None:
            return {
                "points": [
                    {
                        "payload": {
                            "content": "Un fragmento sobre apego ansioso.",
                            "metadata": {
                                "book_title": "Libro de Apego",
                                "category": "Relaciones",
                                "source": "apego.pdf",
                            },
                        }
                    },
                    {
                        "payload": {
                            "content": "Otro fragmento del mismo libro.",
                            "metadata": {
                                "book_title": "Libro de Apego",
                                "category": "Relaciones",
                                "source": "apego.pdf",
                            },
                        }
                    },
                ],
                "next_page_offset": "page-2",
            }
        return {
            "points": [
                {
                    "payload": {
                        "content": "Un fragmento de liderazgo.",
                        "metadata": {
                            "book_title": "Disciplina y Liderazgo",
                            "category": "Negocios",
                            "source": "liderazgo.pdf",
                        },
                    }
                }
            ],
            "next_page_offset": None,
        }


def test_scan_book_index_groups_chunks_by_book_and_category():
    client = FakeQdrantClient()
    books = scan_book_index(client, page_limit=2, max_points=10)

    assert len(books) == 2
    assert client.calls == 2

    relaciones = [book for book in books.values() if book["category"] == "Relaciones"][0]
    negocios = [book for book in books.values() if book["category"] == "Negocios"][0]

    assert relaciones["title"] == "Libro de Apego"
    assert relaciones["chunksCount"] == 2
    assert "apego ansioso" in relaciones["sample"]
    assert negocios["title"] == "Disciplina y Liderazgo"
    assert negocios["chunksCount"] == 1
