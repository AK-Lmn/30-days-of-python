from pathlib import Path
from organizer.history import HistoryManager
from organizer.models import OrganizeAction


def test_history_manager_session_workflow(tmp_path: Path):
    db_file = tmp_path / 'history.db'
    mgr = HistoryManager(db_file)

    src = tmp_path / 'src' / 'document.pdf'
    dst = tmp_path / 'dest' / 'Documents' / 'document.pdf'
    actions = [
        OrganizeAction(
            source_path=src,
            destination_path=dst,
            category='Documents',
            action_type='move',
            size=1024,
            checksum='abc123hash',
        )
    ]

    session_id = mgr.record_session(tmp_path / 'src', 'category', actions)
    assert session_id > 0

    sessions = mgr.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]['id'] == session_id
    assert sessions[0]['undone'] == 0

    active_session = mgr.get_last_active_session()
    assert active_session is not None
    active_id, loaded_actions = active_session
    assert active_id == session_id
    assert len(loaded_actions) == 1
    assert loaded_actions[0].action_type == 'move'
    assert loaded_actions[0].category == 'Documents'

    mgr.mark_session_undone(session_id)
    assert mgr.get_last_active_session() is None

    sessions_updated = mgr.list_sessions()
    assert sessions_updated[0]['undone'] == 1
