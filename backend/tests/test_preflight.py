from pathlib import Path
import socket

from scripts.preflight import is_cloud_path, port_is_free, translation_issues


def test_cloud_sync_path_detection_is_platform_neutral():
    assert is_cloud_path(r"C:\Users\farmer\OneDrive\YojanaSuno")
    assert is_cloud_path("/Users/farmer/Library/Mobile Documents/com~apple~CloudDocs/yojanasuno")
    assert is_cloud_path("/Users/farmer/Dropbox/yojanasuno")
    assert not is_cloud_path("/home/farmer/projects/yojanasuno")


def test_frontend_language_picker_and_labels_are_complete():
    assert translation_issues() == []


def test_port_check_reports_a_port_held_by_this_test_as_busy():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); sock.listen()
        assert not port_is_free("127.0.0.1", sock.getsockname()[1])
