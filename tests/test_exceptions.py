"""Tests for regix.exceptions — all exception types."""
from regix.exceptions import BackendError, ConfigError, GitDirtyError, GitRefError, RegixError

class TestRegixError:

    def test_base_exception(self) -> None:
        err = RegixError('boom')
        assert str(err) == 'boom'
        assert isinstance(err, Exception)

class TestGitRefError:

    def test_simple(self) -> None:
        err = GitRefError('bad-ref')
        assert 'bad-ref' in str(err)
        assert err.ref == 'bad-ref'

    def test_with_detail(self) -> None:
        err = GitRefError('HEAD~99', detail='not found')
        assert 'HEAD~99' in str(err)
        assert 'not found' in str(err)

    def test_is_regix_error(self) -> None:
        assert issubclass(GitRefError, RegixError)

class TestGitDirtyError:

    def test_message_contains_count(self) -> None:
        err = GitDirtyError(['a.py', 'b.py', 'c.py'])
        assert '3' in str(err)
        assert err.dirty_files == ['a.py', 'b.py', 'c.py']

class TestBackendError:

    def test_simple(self) -> None:
        err = BackendError('lizard')
        assert 'lizard' in str(err)
        assert err.backend == 'lizard'
        assert err.cause is None

    def test_with_cause(self) -> None:
        cause = RuntimeError('segfault')
        err = BackendError('radon', cause=cause)
        assert 'radon' in str(err)
        assert 'segfault' in str(err)
        assert err.cause is cause

class TestConfigError:

    def test_simple(self) -> None:
        err = ConfigError('missing key')
        assert 'missing key' in str(err)
        assert err.path is None

    def test_with_path(self) -> None:
        err = ConfigError('bad value', path='regix.yaml')
        assert 'regix.yaml' in str(err)
        assert err.path == 'regix.yaml'