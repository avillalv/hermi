import hermi
import hermi_worker


def test_worker_imports_api():
    assert hermi_worker.__doc__ and hermi.__doc__
