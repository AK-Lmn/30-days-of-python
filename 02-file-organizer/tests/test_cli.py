from pathlib import Path
from click.testing import CliRunner
from organizer.cli import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'organizer' in result.output


def test_cli_organize_and_undo_flow(tmp_path: Path):
    db_file = tmp_path / 'cli_history.db'
    work_dir = tmp_path / 'downloads'
    work_dir.mkdir()
    pdf_file = work_dir / 'report.pdf'
    pdf_file.write_text('PDF content', encoding='utf-8')

    runner = CliRunner()
    dry_res = runner.invoke(cli, ['--db', str(db_file), 'organize', str(work_dir), '--dry-run'])
    assert dry_res.exit_code == 0
    assert 'Dry-Run Plan' in dry_res.output
    assert pdf_file.exists()

    live_res = runner.invoke(cli, ['--db', str(db_file), 'organize', str(work_dir)])
    assert live_res.exit_code == 0
    assert (work_dir / 'Documents' / 'report.pdf').exists()
    assert not pdf_file.exists()

    hist_res = runner.invoke(cli, ['--db', str(db_file), 'history'])
    assert hist_res.exit_code == 0
    assert 'Active' in hist_res.output

    undo_res = runner.invoke(cli, ['--db', str(db_file), 'undo'])
    assert undo_res.exit_code == 0
    assert 'Rollback Successful' in undo_res.output
    assert pdf_file.exists()
    assert not (work_dir / 'Documents' / 'report.pdf').exists()


def test_cli_organize_empty_dir(tmp_path: Path):
    runner = CliRunner()
    res = runner.invoke(cli, ['organize', str(tmp_path)])
    assert res.exit_code == 0
    assert 'No eligible files found' in res.output


def test_cli_undo_no_sessions(tmp_path: Path):
    db_file = tmp_path / 'empty_hist.db'
    runner = CliRunner()
    res = runner.invoke(cli, ['--db', str(db_file), 'undo'])
    assert res.exit_code == 0
    assert 'No active session found' in res.output


def test_cli_duplicates(tmp_path: Path):
    db_file = tmp_path / 'cli_history.db'
    f1 = tmp_path / 'file_a.txt'
    f2 = tmp_path / 'file_b.txt'
    f1.write_text('same data', encoding='utf-8')
    f2.write_text('same data', encoding='utf-8')

    runner = CliRunner()
    res = runner.invoke(cli, ['--db', str(db_file), 'duplicates', str(tmp_path)])
    assert res.exit_code == 0
    assert 'Duplicate Files Found' in res.output


def test_cli_clean_empty(tmp_path: Path):
    empty_sub = tmp_path / 'empty_sub'
    empty_sub.mkdir()
    runner = CliRunner()
    dry_res = runner.invoke(cli, ['clean-empty', str(tmp_path), '--dry-run'])
    assert dry_res.exit_code == 0
    assert 'Empty Folders to Remove' in dry_res.output
    assert empty_sub.exists()

    live_res = runner.invoke(cli, ['clean-empty', str(tmp_path)])
    assert live_res.exit_code == 0
    assert 'Removed Empty Folders' in live_res.output
    assert not empty_sub.exists()


def test_cli_config_commands(tmp_path: Path):
    runner = CliRunner()
    cfg_file = tmp_path / 'custom_organizer.yaml'
    init_res = runner.invoke(cli, ['config', 'init', '--path', str(cfg_file)])
    assert init_res.exit_code == 0
    assert cfg_file.exists()

    show_res = runner.invoke(cli, ['config', 'show', '--config', str(cfg_file)])
    assert show_res.exit_code == 0
    assert 'Active File Categories:' in show_res.output
