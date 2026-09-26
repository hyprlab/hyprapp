"""Transactions and sessions: a savepoint rolls back instead of committing."""
from hyprapp.models import Setting, db



def test_a_savepoint_rolls_back_with_its_transaction(app):
    """The sqlite3 driver's own transaction handling commits a released
    savepoint; SQLAlchemy begins transactions itself so it doesn't."""
    with app.app_context():
        with db.session.begin_nested():
            db.session.add(Setting(key="kept-only-if-committed", value="1"))
        db.session.rollback()
        assert db.session.get(Setting, "kept-only-if-committed") is None
        try:
            with db.session.begin_nested():
                db.session.add(Setting(key="inner", value="1"))
                raise ValueError
        except ValueError:
            pass
        db.session.add(Setting(key="outer", value="1"))
        db.session.commit()
        assert db.session.get(Setting, "inner") is None and db.session.get(Setting, "outer").value == "1"
