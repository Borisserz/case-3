from case3.llm_client import build_body


def test_text_only_message_shape():
    body = build_body(system="sys", user_text="hello", image_urls=())
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["content"][0] == {"type": "text", "text": "hello"}
    assert "model" not in body


def test_with_image_and_model():
    body = build_body(
        system="s",
        user_text="u",
        image_urls=["data:image/png;base64,xx"],
        model="qwen",
    )
    assert body["model"] == "qwen"
    assert body["messages"][1]["content"][1]["type"] == "image_url"
