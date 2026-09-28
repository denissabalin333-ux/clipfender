from backend.services.edit_filter import is_edit_material


def test_edit_filter_keeps_useful_scene():
    assert is_edit_material({"title": "Jon Snow battle scene 4k"}) is True


def test_edit_filter_blocks_obvious_non_editing_content():
    assert is_edit_material({"title": "Jon Snow reaction podcast"}) is False
