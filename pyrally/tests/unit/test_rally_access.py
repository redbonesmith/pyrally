import time

from mock import patch, Mock
from nose.tools import assert_equal, assert_raises, assert_false

from pyrally.rally_access import RallyAccessor, get_accessor, MEM_CACHE


@patch('pyrally.rally_access.ACCESSOR')
@patch('pyrally.rally_access.RallyAccessor')
def test_get_accessor_returns_created_accessor_if_available(RallyAccessor,
                                                            ACCESSOR):
    """
    Test ``get_accessor`` returns created.

    Test that :py:func:`~pyrally.rally_access.get_accessor` returns the created
    accessor if it is available.
    """
    assert_equal(get_accessor(), ACCESSOR)
    assert_false(RallyAccessor.called)


@patch('pyrally.rally_access.ACCESSOR', None)
@patch('pyrally.rally_access.RallyAccessor')
def test_get_accessor_creates_accessor_if_not_already_created(RallyAccessor):
    """
    Test ``get_accessor`` returns created.

    Test that :py:func:`~pyrally.rally_access.get_accessor` creates
    and returns a :py:class:`~pyrally.rally_access.RallyAccessor` object if it
    has not already been created.
    """
    assert_equal(get_accessor('uname', 'pword', 'base_url'),
                 RallyAccessor.return_value)
    assert_equal(RallyAccessor.call_args[0], ('uname', 'pword', 'base_url'))


@patch('pyrally.rally_access.ACCESSOR', None)
@patch('pyrally.rally_access.RallyAccessor')
def test_get_accessor_raises_exception_if_not_created_and_no_uname_password(
                                                                RallyAccessor):
    """
    Test ``get_accessor`` raises Exception.

    Test that :py:func:`~pyrally.rally_access.get_accessor` raises an Exception
    if global ACCESSOR is None and called with no username and password
    arguments.
    """
    assert_raises(Exception, get_accessor)
    assert_false(RallyAccessor.called)


def test_make_url_safe():
    """Test that :py:meth:`.RallyAccessor.make_url_safe` works correctly."""
    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    for url, expected_outcome in [
                                    (' ', "%20"),
                                    ('(', "%28"),
                                    (')', "%29"),
                                    ('"', "%22"),
                                    ('(Hello = "Fred")',
                                     '%28Hello%20=%20%22Fred%22%29')]:
        assert_equal(my_accessor.make_url_safe(url), expected_outcome)


@patch('pyrally.rally_access.urllib2')
def test_make_api_call_full_url_cached(urllib2):
    """
    Test ``make_api_call`` with full, cached url.

    Tests that :py:meth:`~.RallyAccessor.make_api_call`:
        * looks in the cache first and does not make a urllib call.
        * uses the url given without amendments.
        * makes the url given safe.
    """
    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.get_from_cache = Mock()
    my_accessor.make_url_safe = Mock()
    my_accessor.make_url_safe.return_value = 'safe-url'
    my_accessor.get_from_cache.return_value = 'Data'

    response = my_accessor.make_api_call('some-url', full_url=True)

    assert_equal(response, 'Data')
    assert_equal(my_accessor.make_url_safe.call_args[0], ('some-url',))
    assert_equal(my_accessor.get_from_cache.call_args[0], ('safe-url',))
    assert_false(urllib2.urlopen.called)


@patch('pyrally.rally_access.urllib2')
def test_make_api_call_partial_url_not_cached(urllib2):
    """
    Test ``make_api_call`` with partial url, not cached.

    Tests that :py:meth:`~.RallyAccessor.make_api_call`:
        * makes a call to the API via urllib.
        * prepends the api_url to the partial url.
        * makes the url given safe.
        * stores the new data in the cache.
    """
    MEM_CACHE.clear()

    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.api_url = 'http://dummy_url/'

    my_accessor.get_from_cache = Mock()
    my_accessor.set_to_cache = Mock()
    my_accessor.make_url_safe = Mock()
    my_accessor._get_json_response = Mock()
    my_accessor.make_url_safe.return_value = 'safe-url'
    my_accessor.get_from_cache.return_value = False

    my_accessor._get_json_response.return_value = 'python_dict'

    response = my_accessor.make_api_call('some-url', full_url=True)

    assert_equal(response, 'python_dict')
    assert_equal(my_accessor.make_url_safe.call_args[0], ('some-url',))
    assert_equal(my_accessor._get_json_response.call_args[0],
                 (urllib2.Request.return_value,))
    assert_equal(my_accessor.get_from_cache.call_args[0], ('safe-url',))
    assert_equal(my_accessor.set_to_cache.call_args[0], ('safe-url',
                                                         'python_dict'))


def test_set_cache_timeout():
    """Test ``set_cache_timeout`` adds the timeout given correctly.

    Tests :py:meth:`~.RallyAccessor.set_cache_timeout`.
    """
    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.set_cache_timeout('object_name', 10)

    assert_equal(my_accessor.cache_timeouts, {'object_name': 10})


def test_delete_from_cache_removes_correctly():
    """Test ``delete_from_cache`` removes the correct key from the cache.

    Tests :py:meth:`~.RallyAccessor.delete_from_cache`.
    """
    MEM_CACHE.clear()
    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    MEM_CACHE['cache_key']['cache_lookup'] = 'some_test_data'

    my_accessor.delete_from_cache('cache_key', 'cache_lookup')

    assert_equal(MEM_CACHE, {'cache_key': {}})


def test_delete_from_cache_handles_missing_key():
    """Test ``delete_from_cache`` handles missing key being deleted.

    Tests that :py:meth:`~.RallyAccessor.delete_from_cache` does not raise an
    exception when a key is deleted that doesn't exist.
    """
    MEM_CACHE.clear()
    my_accessor = RallyAccessor('uname', 'pword', 'base_url')

    my_accessor.delete_from_cache('story', 'key')

    assert_equal(MEM_CACHE, {'story': {}})


def test_get_cacheable_info():
    """
    Test ``get_cacheable_info``.

    Tests that :py:meth:`~.RallyAccessor.get_cacheable_info`:
        * returns the right cache key and index
    """
    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.api_url = 'http://dummy_url/'

    for url, expected_tuple in [
                ('obj.js?query=something', ('obj_query', 'query=something')),
                ('obj/303923.js', ('obj', '303923')),
                ]:
        full_url = "{0}{1}".format(my_accessor.api_url, url)
        assert_equal(my_accessor.get_cacheable_info(full_url), expected_tuple)


def test_get_from_cache_retrieves_correctly():
    """
    Test ``get_from_cache``.

    Tests that :py:meth:`~.RallyAccessor.get_from_cache`:
        * returns the data at the specified cache location if present
        * returns False if not present
    """
    MEM_CACHE.clear()
    MEM_CACHE['cache_key']['cache_lookup'] = ('data', time.time())

    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.get_cacheable_info = Mock()
    my_accessor.cache_timeouts = Mock()
    my_accessor.cache_timeouts.get.return_value = 10

    for (key, index), expected_result in [
                                    (('cache_key', 'cache_lookup'), 'data'),
                                    (('another_key', 'another_lookup'), False),
                                    ]:
        my_accessor.get_cacheable_info.reset_mock()
        my_accessor.get_cacheable_info.return_value = (key, index)

        assert_equal(my_accessor.get_from_cache('url'), expected_result)

        assert_equal(my_accessor.get_cacheable_info.call_args[0], ('url',))
        assert_equal(my_accessor.cache_timeouts.get.call_args[0],
                           (key, my_accessor.default_cache_timeout))


def test_get_from_cache_returns_false_if_out_of_date():
    """
    Test ``get_from_cache``.

    Tests that :py:meth:`~.RallyAccessor.get_from_cache`:
        * returns False if data is out of date
    """
    MEM_CACHE.clear()
    MEM_CACHE['cache_key']['cache_lookup'] = ('data', 0)

    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.get_cacheable_info = Mock()
    my_accessor.cache_timeouts = Mock()
    my_accessor.cache_timeouts.get.return_value = 0

    my_accessor.get_cacheable_info.return_value = ('cache_key', 'cache_lookup')

    assert_equal(my_accessor.get_from_cache('url'), False)


@patch('pyrally.rally_access.time')
def test_set_to_cache_adds_correctly(time_import):
    """
    Test ``set_to_cache``.

    Tests that :py:meth:`~.RallyAccessor.set_to_cache`:
        * adds the given data to the cache.
    """
    MEM_CACHE.clear()

    my_accessor = RallyAccessor('uname', 'pword', 'base_url')
    my_accessor.get_cacheable_info = Mock()
    my_accessor.get_cacheable_info.return_value = ('cache_key', 'cache_lookup')

    my_accessor.set_to_cache('url', 'set_to_cache_test')

    assert_equal(my_accessor.get_cacheable_info.call_args[0], ('url',))
    assert_equal(MEM_CACHE,
                 {'cache_key':
                    {'cache_lookup':
                        ('set_to_cache_test',
                         time_import.time.return_value)}})

