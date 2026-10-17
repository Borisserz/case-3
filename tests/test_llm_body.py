from case3.llm_client import build_body


def test_text_message_shape():
    body = build_body(system="sys", user_text="hello")
    assert body["messages"][1]["content"] == "hello"
