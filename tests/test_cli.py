"""The flask commands an operator runs inside the container."""
import sqlite3


def test_create_user_and_reset_password(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-user", "ops@example.com", "--admin"],
                           input="password1\npassword1\n")
    assert result.exit_code == 0, result.output
    result = runner.invoke(args=["reset-password", "OPS@example.com"],
                           input="password2\npassword2\n")
    assert result.exit_code == 0, result.output
    from hyprapp.models import User
    with app.app_context():
        assert User.query.one().check_password("password2")


def test_create_user_refuses_a_short_password(app):
    result = app.test_cli_runner().invoke(args=["create-user", "a@example.com"],
                                          input="short\nshort\n")
    assert result.exit_code != 0


def test_backup_writes_a_readable_copy(app, tmp_path):
    dest = tmp_path / "copy.db"
    result = app.test_cli_runner().invoke(args=["backup", str(dest)])
    assert result.exit_code == 0, result.output
    tables = {r[0] for r in sqlite3.connect(dest).execute("SELECT name FROM sqlite_master")}
    assert {"users", "items", "settings"} <= tables


# ———— characterization ————

def users(app):
    from hyprapp.models import User
    with app.app_context():
        return {u.username: (u.name, u.is_admin) for u in User.query.all()}


def test_create_user_says_what_it_made(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-user", "  Ops@Example.com ", "--admin", "--name", "Ops"],
                           input="password1\npassword1\n")
    assert result.output.endswith("Created ops@example.com (admin).\n")
    result = runner.invoke(args=["create-user", "plain@example.com"], input="password1\npassword1\n")
    assert result.output.endswith("Created plain@example.com.\n")
    assert users(app) == {"ops@example.com": ("Ops", True), "plain@example.com": (None, False)}


def test_create_user_refusals(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-user", "not-an-email"])
    assert result.exit_code == 1 and "Error: The username must be an email address." in result.output
    runner.invoke(args=["create-user", "a@example.com"], input="password1\npassword1\n")
    result = runner.invoke(args=["create-user", "A@example.com"])
    assert result.exit_code == 1 and "Error: a@example.com already exists." in result.output
    result = runner.invoke(args=["create-user", "b@example.com"], input="short\nshort\n")
    assert "Error: Passwords need at least 8 characters." in result.output
    assert "b@example.com" not in users(app)


def test_reset_password_refusals_and_output(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["reset-password", "ghost@example.com"])
    assert result.exit_code == 1 and "Error: No account called ghost@example.com." in result.output
    runner.invoke(args=["create-user", "a@example.com"], input="password1\npassword1\n")
    result = runner.invoke(args=["reset-password", "a@example.com"], input="short\nshort\n")
    assert result.exit_code == 1 and "Passwords need at least 8 characters." in result.output
    result = runner.invoke(args=["reset-password", "a@example.com"], input="password2\npassword2\n")
    assert result.output.endswith("Password updated for a@example.com.\n")


def test_backup_refusals(app, tmp_path):
    runner = app.test_cli_runner()
    taken = tmp_path / "taken.db"
    taken.write_text("")
    result = runner.invoke(args=["backup", str(taken)])
    assert result.exit_code == 1 and f"Error: {taken} already exists." in result.output
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://somewhere/db"
    result = runner.invoke(args=["backup", str(tmp_path / "new.db")])
    assert result.exit_code == 1
    assert "Error: backup only knows how to copy a SQLite database." in result.output


def test_backup_reports_the_size(app, tmp_path):
    dest = tmp_path / "copy.db"
    result = app.test_cli_runner().invoke(args=["backup", str(dest)])
    assert result.output == f"Backed up to {dest} ({dest.stat().st_size // 1024} KB).\n"


def test_turnstile_status_from_the_environment(app):
    app.config["TURNSTILE_SITE_KEY"] = "env-site"
    app.config["TURNSTILE_SECRET_KEY"] = "env-secret"
    result = app.test_cli_runner().invoke(args=["turnstile", "status"])
    assert result.output == "Turnstile is on, site key env-site, from the environment.\n"
