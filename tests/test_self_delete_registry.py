from bot.self_delete_registry import consume, mark


def test_mark_then_consume_returns_true_once():
    mark(123, 456)
    assert consume(123, 456) is True
    assert consume(123, 456) is False  # مصرف شد، بارِ دوم دیگه True نیست


def test_consume_without_mark_returns_false():
    assert consume(999, 999) is False


def test_mark_is_scoped_to_chat_id():
    mark(1, 1)
    assert consume(2, 1) is False  # چتِ متفاوت، همون message_id
    assert consume(1, 1) is True
