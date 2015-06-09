import abc
import collections
from functools import partial

from plone import api
from plone.app import testing
from zope.interface.verify import verifyObject

from ..interfaces import ISiteSearch, ISearchResponse, ISearchResult
from ..testing import login_session, TEST_USER_1_NAME


class SiteSearchTestBaseMixin(object):
    """Protocl for implementator to provide the object under test."""

    @abc.abstractmethod
    def _make_utility(self, *args, **kw):
        """Return the utility under test."""

    def _record_debug_info(self, query_response):
        """This is a hook that allows sub-classes to record query responses.

        Useful for debugging tests.
        """

    def _query(self, util, *args, **kw):
        response = util.query(*args, **kw)
        self._record_debug_info(response)
        return response


class SiteSearchContentsTestMixin(SiteSearchTestBaseMixin):
    """Defines a comment set of content re-usable accross different  cases."""

    def setUp(self):
        super(SiteSearchContentsTestMixin, self).setUp()
        container = self.layer['portal']
        create_doc = partial(self._create_content,
                             type='Document',
                             container=container,
                             safe_id=False)
        self.doc1 = create_doc(
            title=u'Test Doc 1',
            description=(u'This is a test document. '
                         u'Hopefully some stuff will be indexed.'),
            subject=(u'test', u'my-tag',),
            safe_id=False
        )
        self.doc2 = create_doc(
            title=u'Test Doc 2',
            description=(u'This is another test document. '
                         u'Please let some stuff be indexed.'),
            subject=(u'test', u'my-other-tag',),
        )
        self.doc3 = create_doc(
            title=u'Lucid Dreaming',
            description=(
                u'An interesting prose by Richard Feynman '
                u'which may leave the casual reader perplexed.'),
        )
        self.doc4 = create_doc(
            title=u'Weather in Wales',
            description=u'Its raining cats and dogs, usually.',
            subject=(u'trivia', u'boredom', u'british-hangups')
        )


class SiteSearchTestsMixin(SiteSearchContentsTestMixin):
    """Defines the base test case for the search utility.

    Each implementor of ISiteSite should implement at least one
    sub-test case.

    :seealso: The search utility API is described by
              ploneintranet.search.interfaces.ISiteSearch
    """

    def _check_type_iterable(self, response):
        self.assertIsInstance(response, collections.Iterable)
        result = next(iter(response), None)
        self.assertIsNotNone(result)

    def test_reponse_iterable(self):
        util = self._make_utility()
        response = util.query('hopefully')
        self._check_type_iterable(response)

    def test_results_iterable(self):
        util = self._make_utility()
        response = util.query('hopefully')
        self._check_type_iterable(response.results)

    def test_interface_compliance(self):
        util = self._make_utility()
        verifyObject(ISiteSearch, util)
        search_response = util.query(
            'Test',
            # Use a filter to avoid zcatalog MissingValue serialization issues
            # due to the 'robot-test-folder' persisting in tests.
            filters=dict(friendly_type_name='Page')
        )
        verifyObject(ISearchResponse, search_response)
        for search_result in search_response:
            verifyObject(ISearchResult, search_result)

    def test_query_phrase_only(self):
        util = self._make_utility()
        response = self._query(util, 'hopefully')
        result = next(iter(response), None)
        self.assertIsNotNone(result)
        self.assertEqual(result.title, self.doc1.Title())
        self.assertEqual(result.url, self.doc1.absolute_url())
        self.assertEqual(response.total_results, 1)
        self.assertEqual(set(response.facets['friendly_type_name']), {'Page'})
        self.assertEqual(set(response.facets['tags']), {u'test', u'my-tag'})

    def test_query_with_empty_filters(self):
        util = self._make_utility()
        response = util.query(u'stuff', filters={})
        expected_facets = {u'test', u'my-tag', u'my-other-tag'}
        self.assertSetEqual(response.facets['tags'], expected_facets)
        self.assertSetEqual(response.facets['friendly_type_name'], {'Page'})

    def test_query_facets_invalid(self):
        util = self._make_utility()
        self.assertRaises(LookupError,
                          util.query,
                          u'stuff',
                          filters=dict(ploneineternet=u'mytag'))

    def test_query_tags_facet(self):
        util = self._make_utility()
        response = self._query(util, 'stuff')
        self.assertEqual(response.total_results, 2)
        expected_facets = {u'test', u'my-tag', u'my-other-tag'}
        self.assertEqual(set(response.facets['tags']), expected_facets)
        # Limit search by a tag from one of the docs//
        response = self._query(util, 'stuff',
                               filters={'tags': [u'my-other-tag']})
        self.assertEqual(response.total_results, 1)
        expected_tags = {u'test', u'my-other-tag'}
        self.assertEqual(set(response.facets['tags']), expected_tags)

    def test_query_friendly_type_facet(self):
        util = self._make_utility()
        response = self._query(util, 'hopefully')
        self.assertEqual(response.total_results, 1)
        expected_ft_facets = {'Page'}
        actual_ft_facets = set(response.facets['friendly_type_name'])
        self.assertEqual(actual_ft_facets, expected_ft_facets)
        response = self._query(util, 'stuff')
        self.assertEqual(response.total_results, 2)
        expected_ft_facets = {'Page'}
        actual_ft_facets = set(response.facets['friendly_type_name'])
        self.assertSetEqual(actual_ft_facets, expected_ft_facets)

    def test_batching_returns_all_tags(self):
        util = self._make_utility()
        response = self._query(util, u'stuff', step=1)
        self.assertEqual(response.total_results, 2)
        self.assertEqual(len(list(response)), 1)
        expected_tags = {u'test', u'my-tag', u'my-other-tag'}
        self.assertEqual(set(response.facets['tags']), expected_tags)

    def test_delete_content(self):
        util = self._make_utility()

        def query_check_total_results(expected_count):
            response = self._query(util, u'Another')
            self.assertEqual(response.total_results, expected_count)

        query_check_total_results(1)
        with api.env.adopt_roles(roles=['Manager']):
            self._delete_content(self.doc2)
        assert self.doc2.getId() not in self.layer['portal'].keys()
        query_check_total_results(0)

    def _check_spellcheck_response(self, query_term, expect_suggestion):
        util = self._make_utility()
        response = self._query(util, query_term)
        self.assertEqual(response.spell_corrected_search, expect_suggestion)

    def test_spell_corrected_search(self):
        self._check_spellcheck_response(None, None)
        self._check_spellcheck_response('', None)
        self._check_spellcheck_response(u'', None)
        self._check_spellcheck_response(u'*:*', None)

        # Test a correctly spelt terms have no spell_corrected_search
        self._check_spellcheck_response(u'Lucid', None)
        self._check_spellcheck_response(u'leave', None)
        self._check_spellcheck_response(u'Test', None)

        # These corrected spellings should work (depending on configuration.
        self._check_spellcheck_response(u'anathar', u'another')
        self._check_spellcheck_response(u'Rcichad', u'Richard')
        self._check_spellcheck_response(u'Anather', u'Another')
        self._check_spellcheck_response(u'Perplaxed', u'Perplexed')
        self._check_spellcheck_response(u"Reining cots n' dags",
                                        u"Raining cats n' dogs")


class SiteSearchPermissionTestsMixin(SiteSearchContentsTestMixin):
    """Permissions tests.

    These tests should ensure combinations of users and roles can
    only see the content they are permitted by the permissions system.
    """

    def setUp(self):
        super(SiteSearchPermissionTestsMixin, self).setUp()
        testing.login(self.layer['portal'], testing.TEST_USER_NAME)

    def test_documents_owned_by_other_not_visible_same_role(self):
        with login_session(TEST_USER_1_NAME):
            util = self._make_utility()
            response = self._query(util, 'Test Doc')
            self.assertEqual(response.total_results, 0)

    def test_review_state_changes(self):
        """Does the search respect view permissions?"""
        api.content.transition(obj=self.doc2, transition='publish')
        testing.logout()
        util = self._make_utility()

        # Check anonymous access
        response = self._query(util, 'hopefully')
        self.assertEqual(response.total_results, 0)
        response = self._query(util, 'another')
        self.assertEqual(response.total_results, 1)

        with login_session(TEST_USER_1_NAME):
            response = self._query(util, 'hopefully')
            self.assertEqual(response.total_results, 0)
            response = self._query(util, 'another')
            self.assertEqual(response.total_results, 1)

            with api.env.adopt_roles(['Manager']):
                api.content.transition(obj=self.doc1, transition='publish')

            response = self._query(util, 'hopefully')
            self.assertEqual(response.total_results, 1)
