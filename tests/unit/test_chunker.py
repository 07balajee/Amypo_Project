from app.ingest.chunker import chunk_text


def test_sections_become_chunks_with_heading_trail():
    text = "# Policy\n\n## Fees\n\nPay by July 15.\n\n## Hostel\n\nCurfew is 9:30 PM.\n"
    chunks = chunk_text("doc", text, size_tokens=50, overlap_tokens=5)
    assert [c.chunk_id for c in chunks] == ["doc#c0", "doc#c1"]
    assert chunks[0].text == "Policy > Fees\nPay by July 15."
    assert chunks[1].text.startswith("Policy > Hostel\n")


def test_long_section_is_split_with_overlap():
    words = [f"w{i}" for i in range(100)]
    chunks = chunk_text("d", " ".join(words), size_tokens=40, overlap_tokens=10)
    assert len(chunks) > 1
    assert all(c.token_count <= 40 for c in chunks)
    first, second = chunks[0].text.split(), chunks[1].text.split()
    assert first[-10:] == second[:10]  # overlap carried forward
    covered = {w for c in chunks for w in c.text.split()}
    assert covered == set(words)


def test_empty_text_gives_no_chunks():
    assert chunk_text("d", "   \n\n") == []
