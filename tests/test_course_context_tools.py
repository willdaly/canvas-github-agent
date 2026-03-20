from tools.course_context_tools import CourseContextTools, chunk_markdown_document


class FakeCollection:
    def __init__(self):
        self.records = {}

    def upsert(self, ids, documents, metadatas):
        for record_id, document, metadata in zip(ids, documents, metadatas):
            self.records[record_id] = {
                "id": record_id,
                "document": document,
                "metadata": metadata,
            }

    def get(self, where=None, include=None):
        course_id = None if where is None else where.get("course_id")
        matches = [
            record for record in self.records.values()
            if course_id is None or record["metadata"].get("course_id") == course_id
        ]
        return {
            "metadatas": [record["metadata"] for record in matches],
        }

    def query(self, query_texts, n_results, where=None):
        course_id = None if where is None else where.get("course_id")
        terms = {term.lower() for term in query_texts[0].split() if term.strip()}
        matches = []

        for record in self.records.values():
            metadata = record["metadata"]
            if course_id is not None and metadata.get("course_id") != course_id:
                continue

            document = record["document"].lower()
            overlap = sum(1 for term in terms if term in document)
            if overlap == 0:
                continue

            matches.append((overlap, record))

        matches.sort(key=lambda item: (-item[0], item[1]["id"]))
        chosen = [record for _, record in matches[:n_results]]

        return {
            "ids": [[record["id"] for record in chosen]],
            "documents": [[record["document"] for record in chosen]],
            "metadatas": [[record["metadata"] for record in chosen]],
            "distances": [[1.0 / (index + 1) for index, _ in enumerate(chosen)]],
        }


def test_chunk_markdown_document_splits_sections_and_large_paragraphs():
    markdown = "# Bayes Review\n\n" + ("posterior update " * 120) + "\n\n# Decision Trees\n\nentropy"

    chunks = chunk_markdown_document(markdown, max_chars=200)

    assert len(chunks) >= 3
    assert chunks[0]["section_title"] == "Bayes Review"
    assert any(chunk["section_title"] == "Decision Trees" for chunk in chunks)


def test_course_context_ingest_and_search_round_trip(monkeypatch):
    fake_collection = FakeCollection()
    tools = CourseContextTools()

    monkeypatch.setattr(tools, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(
        tools,
        "_parse_pdf",
        lambda file_path: {
            "document_id": "aai-slides",
            "document_name": "AAI Slides.pdf",
            "source_path": file_path,
            "chunks": [
                {
                    "chunk_index": 0,
                    "section_title": "Bayes Review",
                    "text": "Section: Bayes Review\n\nPosterior update uses Bayes theorem.",
                },
                {
                    "chunk_index": 1,
                    "section_title": "Decision Trees",
                    "text": "Section: Decision Trees\n\nEntropy and information gain.",
                },
            ],
        },
    )

    ingest_result = tools.ingest_pdf(6660, "docs/slides.pdf")
    documents = tools.list_documents(6660)
    results = tools.search_context(6660, "Bayes posterior update", limit=2)

    assert ingest_result["status"] == "ingested"
    assert ingest_result["chunk_count"] == 2
    assert documents == [
        {
            "course_id": 6660,
            "document_id": "aai-slides",
            "document_name": "AAI Slides.pdf",
            "source_path": "docs/slides.pdf",
            "chunk_count": 2,
        }
    ]
    assert results[0]["section_title"] == "Bayes Review"
    assert "Posterior update" in results[0]["text"]