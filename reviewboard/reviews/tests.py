from __future__ import print_function, unicode_literals

from django.test.client import RequestFactory
from django.utils import six
from django.utils.safestring import SafeText
from kgb import SpyAgency
from reviewboard.reviews.markdown_utils import (get_markdown_element_tree,
                                                markdown_escape,
                                                markdown_unescape,
                                                normalize_text_for_edit,
                                                render_markdown)
from reviewboard.reviews.models import (Comment,
                                        DefaultReviewer,
                                        Group,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Review,
                                        Screenshot)
from reviewboard.reviews.ui.base import (FileAttachmentReviewUI,
                                         register_ui,
                                         unregister_ui)
from reviewboard.scmtools.core import ChangeSet, Commit
from reviewboard.scmtools.errors import ChangeNumberInUseError
from reviewboard.testing import TestCase
    fixtures = ['test_users']

    @add_fixtures(['test_scmtools'])
    def test_create_with_site(self):
        """Testing ReviewRequest.objects.create with LocalSite"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        review_request = ReviewRequest.objects.create(
            user, repository, local_site=local_site)
        self.assertEqual(review_request.repository, repository)
        self.assertEqual(review_request.local_site, local_site)
        self.assertEqual(review_request.local_id, 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id(self):
        """Testing ReviewRequest.objects.create with LocalSite and commit ID"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        review_request = ReviewRequest.objects.create(
            user, repository,
            commit_id='123',
            local_site=local_site)
        self.assertEqual(review_request.repository, repository)
        self.assertEqual(review_request.commit_id, '123')
        self.assertEqual(review_request.local_site, local_site)
        self.assertEqual(review_request.local_id, 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id_conflicts_review_request(self):
        """Testing ReviewRequest.objects.create with LocalSite and
        commit ID that conflicts with a review request
        """
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        # This one should be fine.
        ReviewRequest.objects.create(user, repository, commit_id='123',
                                     local_site=local_site)
        self.assertEqual(local_site.review_requests.count(), 1)

        # This one will yell.
        self.assertRaises(
            ChangeNumberInUseError,
            lambda: ReviewRequest.objects.create(
                user, repository,
                commit_id='123',
                local_site=local_site))

        # Make sure that entry doesn't exist in the database.
        self.assertEqual(local_site.review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id_conflicts_draft(self):
        """Testing ReviewRequest.objects.create with LocalSite and
        commit ID that conflicts with a draft
        """
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        # This one should be fine.
        existing_review_request = ReviewRequest.objects.create(
            user, repository, local_site=local_site)
        existing_draft = ReviewRequestDraft.create(existing_review_request)
        existing_draft.commit_id = '123'
        existing_draft.save()

        self.assertEqual(local_site.review_requests.count(), 1)

        # This one will yell.
        self.assertRaises(
            ChangeNumberInUseError,
            lambda: ReviewRequest.objects.create(
                user, repository,
                commit_id='123',
                local_site=local_site))

        # Make sure that entry doesn't exist in the database.
        self.assertEqual(local_site.review_requests.count(), 1)

    @add_fixtures(['test_scmtools'])
    def test_create_with_site_and_commit_id_and_fetch_problem(self):
        """Testing ReviewRequest.objects.create with LocalSite and
        commit ID with problem fetching commit details
        """
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.create(name='test')
        repository = self.create_repository()

        self.assertEqual(local_site.review_requests.count(), 0)

        ReviewRequest.objects.create(
            user, repository,
            commit_id='123',
            local_site=local_site,
            create_from_commit_id=True)

        # Make sure that entry doesn't exist in the database.
        self.assertEqual(local_site.review_requests.count(), 1)
        review_request = local_site.review_requests.get()
        self.assertEqual(review_request.local_id, 1)
        self.assertEqual(review_request.commit_id, '123')
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        self.create_review_request(summary='Test 1',
                                   publish=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 2',
                                   submitter=user2)
        self.create_review_request(summary='Test 3',
                                   status='S',
                                   public=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 4',
                                   status='S',
                                   public=True,
                                   submitter=user2)
        self.create_review_request(summary='Test 5',
                                   status='D',
                                   public=True,
                                   submitter=user1)
        self.create_review_request(summary='Test 6',
                                   status='D',
                                   submitter=user2)

            ReviewRequest.objects.public(user=user1),
            [
                'Test 1',
            ])
            ReviewRequest.objects.public(status=None),
            [
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 1',
            ])
            ReviewRequest.objects.public(user=user2, status=None),
            [
                'Test 6',
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])
        self.assertValidSummaries(
            ReviewRequest.objects.public(status=None,
                                         show_all_unpublished=True),
            [
                'Test 6',
                'Test 5',
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])
        user1 = User.objects.get(username='doc')

        group1 = self.create_review_group(name='privgroup')
        group1.users.add(user1)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    public=False,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    status='S',
                                                    submitter=user1)
        review_request.target_groups.add(group1)

            [
                'Test 1',
            ])
            [
                'Test 3',
                'Test 1',
            ])
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    public=True,
                                                    status='S')
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)

            [
                'Test 3',
                'Test 1',
            ])
            ReviewRequest.objects.to_user_groups(
                "doc", status=None, local_site=None),
            [
                'Test 3',
                'Test 2',
                'Test 1',
            ])
            ReviewRequest.objects.to_user_groups(
                "grumpy", user=user2, local_site=None),
            [
                'Test 3',
            ])
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    public=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 3',
                                                    public=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    public=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_people.add(user1)

            [
                'Test 3',
            ])
            [
                'Test 4',
                'Test 3',
            ])
            ReviewRequest.objects.to_user_directly(
                "doc", user2, status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 2',
            ])
        user1 = User.objects.get(username='doc')

        self.create_review_request(summary='Test 1',
                                   public=True,
                                   submitter=user1)

        self.create_review_request(summary='Test 2',
                                   public=False,
                                   submitter=user1)

        self.create_review_request(summary='Test 3',
                                   public=True,
                                   status='S',
                                   submitter=user1)

            ReviewRequest.objects.from_user("doc", local_site=None),
            [
                'Test 1',
            ])
            ReviewRequest.objects.from_user("doc", status=None,
                                            local_site=None),
            [
                'Test 3',
                'Test 1',
            ])
            ReviewRequest.objects.from_user(
                "doc", user=user1, status=None, local_site=None),
            [
                'Test 3',
                'Test 2',
                'Test 1',
            ])
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        group1 = self.create_review_group(name='group1')
        group1.users.add(user1)

        group2 = self.create_review_group(name='group2')
        group2.users.add(user2)

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True,
                                                    submitter=user1)
        review_request.target_groups.add(group1)

        review_request = self.create_review_request(summary='Test 2',
                                                    submitter=user2,
                                                    status='S')
        review_request.target_groups.add(group1)
        review_request.target_people.add(user2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 3',
                                                    publish=True,
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)

        review_request = self.create_review_request(summary='Test 4',
                                                    publish=True,
                                                    status='S',
                                                    submitter=user2)
        review_request.target_groups.add(group1)
        review_request.target_groups.add(group2)
        review_request.target_people.add(user1)
            ReviewRequest.objects.to_user("doc", local_site=None),
            [
                'Test 3',
                'Test 1',
            ])
        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc", status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 1',
            ])
            ReviewRequest.objects.to_user(
                "doc", user=user2, status=None, local_site=None),
            [
                'Test 4',
                'Test 3',
                'Test 2',
                'Test 1',
            ])
            self.assertIn(summary, summaries,
                          'summary "%s" not found in summary list'
                          % summary)
            self.assertIn(summary, r_summaries,
                          'summary "%s" not found in review request list'
                          % summary)
class ReviewRequestTests(SpyAgency, TestCase):
    def test_close_removes_commit_id(self):
        """Testing ReviewRequest.close with discarded removes commit ID"""
        review_request = self.create_review_request(publish=True,
                                                    commit_id='123')
        self.assertEqual(review_request.commit_id, '123')
        review_request.close(ReviewRequest.DISCARDED)

        self.assertIsNone(review_request.commit_id)

    @add_fixtures(['test_scmtools'])
    def test_changeset_update_commit_id(self):
        """Testing ReviewRequest.changeset_is_pending update commit ID
        behavior
        """
        current_commit_id = '123'
        new_commit_id = '124'
        review_request = self.create_review_request(
            publish=True,
            commit_id=current_commit_id,
            create_repository=True)
        draft = ReviewRequestDraft.create(review_request)
        self.assertEqual(review_request.commit_id, current_commit_id)
        self.assertEqual(draft.commit_id, current_commit_id)

        def _get_fake_changeset(scmtool, commit_id, allow_empty=True):
            self.assertEqual(commit_id, current_commit_id)

            changeset = ChangeSet()
            changeset.pending = False
            changeset.changenum = int(new_commit_id)
            return changeset

        scmtool = review_request.repository.get_scmtool()
        scmtool.supports_pending_changesets = True
        self.spy_on(scmtool.get_changeset,
                    call_fake=_get_fake_changeset)

        self.spy_on(review_request.repository.get_scmtool,
                    call_fake=lambda x: scmtool)

        is_pending, new_commit_id = \
            review_request.changeset_is_pending(current_commit_id)
        self.assertEqual(is_pending, False)
        self.assertEqual(new_commit_id, new_commit_id)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertEqual(review_request.commit_id, new_commit_id)

        draft = review_request.get_draft()
        self.assertEqual(draft.commit_id, new_commit_id)

    def test_unicode_summary_and_str(self):
        """Testing ReviewRequest.__str__ with unicode summaries."""
        review_request = self.create_review_request(
            summary='\u203e\u203e', publish=True)
        self.assertEqual(six.text_type(review_request), '\u203e\u203e')

    def test_discard_unpublished_private(self):
        """Testing ReviewRequest.close with private requests on discard
        to ensure changes from draft are copied over
        """
        review_request = self.create_review_request(
            publish=False,
            public=False)

        self.assertFalse(review_request.public)
        self.assertNotEqual(review_request.status, ReviewRequest.DISCARDED)

        draft = ReviewRequestDraft.create(review_request)

        summary = 'Test summary'
        description = 'Test description'
        testing_done = 'Test testing done'

        draft.summary = summary
        draft.description = description
        draft.testing_done = testing_done
        draft.save()

        review_request.close(ReviewRequest.DISCARDED)

        latest_changedesc = \
            review_request.changedescs.filter(public=True).latest()

        fields = latest_changedesc.fields_changed

        self.assertIn('summary', fields)
        self.assertIn('description', fields)
        self.assertIn('testing_done', fields)

        self.assertEqual(fields["summary"]["new"][0], summary)
        self.assertEqual(fields["description"]["new"][0], description)
        self.assertEqual(fields["testing_done"]["new"][0], testing_done)

    def test_discard_unpublished_public(self):
        """Testing ReviewRequest.close with public requests on discard
        to ensure changes from draft are not copied over
        """
        review_request = self.create_review_request(
            publish=False,
            public=True)

        self.assertTrue(review_request.public)
        self.assertNotEqual(review_request.status, ReviewRequest.DISCARDED)

        draft = ReviewRequestDraft.create(review_request)

        summary = 'Test summary'
        description = 'Test description'
        testing_done = 'Test testing done'

        draft.summary = summary
        draft.description = description
        draft.testing_done = testing_done
        draft.save()

        review_request.close(ReviewRequest.DISCARDED)

        latest_changedesc = \
            review_request.changedescs.filter(public=True).latest()

        fields = latest_changedesc.fields_changed

        self.assertNotIn('summary', fields)
        self.assertNotIn('description', fields)
        self.assertNotIn('testing_done', fields)
    fixtures = ['test_users', 'test_scmtools', 'test_site']
        super(ViewTests, self).setUp()

    def _get_context_var(self, response, varname):
    def test_review_detail_redirect_no_slash(self):
        """Testing review_detail view redirecting with no trailing slash"""
    def test_review_detail(self):
        """Testing review_detail view"""
        review_request = self.create_review_request(publish=True)
        request = self._get_context_var(response, 'review_request')
    def test_review_detail_context(self):
        """Testing review_detail view's context"""
        username = 'admin'
        summary = 'This is a test summary'
        description = 'This is my description'
        testing_done = 'Some testing'
        review_request = self.create_review_request(
            publish=True,
            submitter=username,
            summary=summary,
            description=description,
            testing_done=testing_done)
        response = self.client.get('/r/%s/' % review_request.pk)
        self.assertEqual(response.status_code, 200)
        request = self._get_context_var(response, 'review_request')
        self.assertEqual(request.submitter.username, username)
        self.assertEqual(request.summary, summary)
        self.assertEqual(request.description, description)
        self.assertEqual(request.testing_done, testing_done)
        self.assertEqual(request.pk, review_request.pk)
        """Testing review_detail and ordering of diff comments on a review"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        main_review = self.create_review(review_request, user=user1)
        main_comment = self.create_diff_comment(main_review, filediff,
                                                text=comment_text_1)
        reply1 = self.create_reply(
            main_review,
            user=user1,
            timestamp=(main_review.timestamp + timedelta(days=1)))
        self.create_diff_comment(reply1, filediff, text=comment_text_2,
                                 reply_to=main_comment)
        reply2 = self.create_reply(
            main_review,
            user=user2,
            timestamp=(main_review.timestamp + timedelta(days=2)))
        self.create_diff_comment(reply2, filediff, text=comment_text_3,
                                 reply_to=main_comment)
    def test_review_detail_sitewide_login(self):

        self.create_review_request(publish=True)

    def test_new_review_request(self):
        """Testing new_review_request view"""
    def test_interdiff(self):
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request, revision=1)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/readme',
            dest_file='/readme',
            source_revision='d6613f5',
            dest_detail='5b50866',
            diff=(
                b'diff --git a/readme b/readme\n'
                b'index d6613f5..5b50866 100644\n'
                b'--- a/readme\n'
                b'+++ b/readme\n'
                b'@@ -1 +1,3 @@\n'
                b' Hello there\n'
                b'+\n'
                b'+Oh hi!\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd3\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a new file!\n'
            ))

        diffset = self.create_diffset(review_request, revision=2)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/readme',
            dest_file='/readme',
            source_revision='d6613f5',
            dest_detail='5b50867',
            diff=(
                b'diff --git a/readme b/readme\n'
                b'index d6613f5..5b50867 100644\n'
                b'--- a/readme\n'
                b'+++ b/readme\n'
                b'@@ -1 +1,3 @@\n'
                b' Hello there\n'
                b'+----------\n'
                b'+Oh hi!\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd4\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a diffent version of this new file!\n'
            ))

        response = self.client.get('/r/1/diff/1-2/')
            print("Error: %s" % self._get_context_var(response, 'error'))
            print(self._get_context_var(response, 'trace'))
        self.assertEqual(
            self._get_context_var(response, 'diff_context')['num_diffs'],
            2)
        files = self._get_context_var(response, 'files')
        self.assertTrue(files)
        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])
        self.assertEqual(files[1]['depot_filename'], '/readme')
        self.assertIn('interfilediff', files[1])
    def test_interdiff_new_file(self):
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request, revision=1)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))

        diffset = self.create_diffset(review_request, revision=2)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd4\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a diffent version of this new file!\n'
            ))

        response = self.client.get('/r/1/diff/1-2/')
            print("Error: %s" % self._get_context_var(response, 'error'))
            print(self._get_context_var(response, 'trace'))
        self.assertEqual(
            self._get_context_var(response, 'diff_context')['num_diffs'],
            2)
        files = self._get_context_var(response, 'files')
        self.assertTrue(files)
        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff,
                                           issue_opened=True)
    # Bug #3384
    def test_diff_raw_content_disposition_attachment(self):
        """Testing /diff/raw/ Content-Disposition: attachment; ..."""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        self.create_diffset(review_request=review_request)

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename=diffset')

    fixtures = ['test_users', 'test_scmtools']
    def test_draft_changes(self):
        draft = self._get_draft()
        self.assertIn("summary", fields)
        self.assertIn("description", fields)
        self.assertIn("testing_done", fields)
        self.assertIn("branch", fields)
        self.assertIn("bugs_closed", fields)
    def _get_draft(self):
        """Convenience function for getting a new draft to work with."""
        review_request = self.create_review_request(publish=True)
        return ReviewRequestDraft.create(review_request)


class FieldTests(TestCase):
    # Bug #1352
    def test_long_bug_numbers(self):
        """Testing review requests with very long bug numbers"""
        review_request = ReviewRequest()
        review_request.bugs_closed = \
            '12006153200030304432010,4432009'
        self.assertEqual(review_request.get_bug_list(),
                         ['4432009', '12006153200030304432010'])

    # Our _("(no summary)") string was failing in the admin UI, as
    # django.template.defaultfilters.stringfilter would fail on a
    # ugettext_lazy proxy object. We can use any stringfilter for this.
    #
    # Bug #1346
    def test_no_summary(self):
        """Testing review requests with no summary"""
        from django.template.defaultfilters import lower
        review_request = ReviewRequest()
        lower(review_request)

    @add_fixtures(['test_users'])
    def test_commit_id(self):
        """Testing commit_id migration"""
        review_request = self.create_review_request()
        review_request.changenum = '123'

        self.assertEqual(review_request.commit_id, None)
        self.assertEqual(review_request.commit,
                         six.text_type(review_request.changenum))
        self.assertNotEqual(review_request.commit_id, None)


class PostCommitTests(SpyAgency, TestCase):
    fixtures = ['test_users', 'test_scmtools']

    def setUp(self):
        super(PostCommitTests, self).setUp()

        self.user = User.objects.create(username='testuser', password='')
        self.profile, is_new = Profile.objects.get_or_create(user=self.user)
        self.profile.save()

        self.testdata_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scmtools', 'testdata')

        self.repository = self.create_repository(tool_name='Test')

    def test_update_from_committed_change(self):
        """Testing post-commit update"""
        commit_id = '4'

        def get_change(repository, commit_to_get):
            self.assertEqual(commit_id, commit_to_get)

            commit = Commit()
            commit.message = \
                'This is my commit message\n\nWith a summary line too.'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')
            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        def get_file_exists(repository, path, revision, base_commit_id=None,
                            request=None):
            return (path, revision) in [('/readme', 'd6613f5')]

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists, call_fake=get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.update_from_commit_id(commit_id)

        self.assertEqual(review_request.summary, 'This is my commit message')
        self.assertEqual(review_request.description,
                         'With a summary line too.')

        self.assertEqual(review_request.diffset_history.diffsets.count(), 1)

        diffset = review_request.diffset_history.diffsets.get()
        self.assertEqual(diffset.files.count(), 1)

        fileDiff = diffset.files.get()
        self.assertEqual(fileDiff.source_file, 'readme')
        self.assertEqual(fileDiff.source_revision, 'd6613f5')

    def test_update_from_committed_change_with_markdown_escaping(self):
        """Testing post-commit update with markdown escaping"""
        def get_change(repository, commit_to_get):
            commit = Commit()
            commit.message = '* No escaping\n\n* but this needs escaping'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')
            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        def get_file_exists(repository, path, revision, base_commit_id=None,
                            request=None):
            return (path, revision) in [('/readme', 'd6613f5')]

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists, call_fake=get_file_exists)
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.description_rich_text = True
        review_request.update_from_commit_id('4')
        self.assertEqual(review_request.summary, '* No escaping')
        self.assertEqual(review_request.description,
                         '\\* but this needs escaping')
    def test_update_from_committed_change_without_repository_support(self):
        """Testing post-commit update failure conditions"""
        self.spy_on(self.repository.__class__.supports_post_commit.fget,
                    call_fake=lambda self: False)
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)

        self.assertRaises(NotImplementedError,
                          lambda: review_request.update_from_commit_id('4'))
    fixtures = ['test_users', 'test_scmtools']
    def test_duplicate_reviews(self):
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        master_review = self.create_review(review_request, user=user,
                                           body_top=body_top,
                                           body_bottom='')
        self.create_diff_comment(master_review, filediff, text=comment_text_1,
                                 first_line=1, num_lines=1)
        review = self.create_review(review_request, user=user,
                                    body_top='', body_bottom='')
        self.create_diff_comment(review, filediff, text=comment_text_2,
                                 first_line=1, num_lines=1)
        review = self.create_review(review_request, user=user,
                                    body_top='',
                                    body_bottom=body_bottom)
        self.create_diff_comment(review, filediff, text=comment_text_3,
                                 first_line=1, num_lines=1)
        self.assertTrue(review)
        self.assertEqual(len(default_reviewers), 2)
        self.assertIn(default_reviewer1, default_reviewers)
        self.assertIn(default_reviewer2, default_reviewers)
        self.assertEqual(len(default_reviewers), 1)
        self.assertIn(default_reviewer2, default_reviewers)
        default_reviewers = DefaultReviewer.objects.for_repository(
            None, test_site)
        self.assertEqual(len(default_reviewers), 1)
        self.assertIn(default_reviewer1, default_reviewers)
        self.assertEqual(len(default_reviewers), 1)
        self.assertIn(default_reviewer2, default_reviewers)
        """Testing DefaultReviewerForm with a User not on the same LocalSite.
        """
        """Testing DefaultReviewerForm with a Group not on the same LocalSite.
        """
        """Testing DefaultReviewerForm with a Repository not on the same
        LocalSite.
        """
    def test_milestones(self):
    def test_palindrome(self):
            "{% ifneatnumber " + six.text_type(rid) + " %}"
class ReviewRequestCounterTests(TestCase):
        super(ReviewRequestCounterTests, self).setUp()

        """Testing counters with reopening discarded outgoing review requests
        """
        """Testing counters with reopening submitted outgoing review requests
        """
class IssueCounterTests(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        super(IssueCounterTests, self).setUp()

        self.review_request = self.create_review_request(publish=True)
        self.assertEqual(self.review_request.issue_open_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        self._reset_counts()

    @add_fixtures(['test_scmtools'])
    def test_init_with_diff_comments(self):
        """Testing ReviewRequest issue counter initialization
        from diff comments
        """
        self.review_request.repository = self.create_repository()

        diffset = self.create_diffset(self.review_request)
        filediff = self.create_filediff(diffset)

        self._test_issue_counts(
            lambda review, issue_opened: self.create_diff_comment(
                review, filediff, issue_opened=issue_opened))

    def test_init_with_file_attachment_comments(self):
        """Testing ReviewRequest issue counter initialization
        from file attachment comments
        """
        file_attachment = self.create_file_attachment(self.review_request)

        self._test_issue_counts(
            lambda review, issue_opened: self.create_file_attachment_comment(
                review, file_attachment, issue_opened=issue_opened))

    def test_init_with_screenshot_comments(self):
        """Testing ReviewRequest issue counter initialization
        from screenshot comments
        """
        screenshot = self.create_screenshot(self.review_request)

        self._test_issue_counts(
            lambda review, issue_opened: self.create_screenshot_comment(
                review, screenshot, issue_opened=issue_opened))

    @add_fixtures(['test_scmtools'])
    def test_init_with_mix(self):
        """Testing ReviewRequest issue counter initialization
        from multiple types of comments at once
        """
        # The initial implementation for issue status counting broke when
        # there were multiple types of comments on a review (such as diff
        # comments and file attachment comments). There would be an
        # artificially large number of issues reported.
        #
        # That's been fixed, and this test is ensuring that it doesn't
        # regress.
        self.review_request.repository = self.create_repository()
        diffset = self.create_diffset(self.review_request)
        filediff = self.create_filediff(diffset)
        file_attachment = self.create_file_attachment(self.review_request)
        screenshot = self.create_screenshot(self.review_request)

        review = self.create_review(self.review_request)

        # One open file attachment comment
        self.create_file_attachment_comment(review, file_attachment,
                                            issue_opened=True)

        # Two diff comments
        self.create_diff_comment(review, filediff, issue_opened=True)
        self.create_diff_comment(review, filediff, issue_opened=True)

        # Four screenshot comments
        self.create_screenshot_comment(review, screenshot, issue_opened=True)
        self.create_screenshot_comment(review, screenshot, issue_opened=True)
        self.create_screenshot_comment(review, screenshot, issue_opened=True)
        self.create_screenshot_comment(review, screenshot, issue_opened=True)

        # The issue counts should be end up being 0, since they'll initialize
        # during load.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        # Now publish. We should have 7 open issues, by way of incrementing
        # during publish.
        review.publish()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 7)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

        # Make sure we get the same number back when initializing counters.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 7)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

    def test_init_with_replies(self):
        """Testing ReviewRequest issue counter initialization and replies."""
        file_attachment = self.create_file_attachment(self.review_request)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(review, file_attachment,
                                                      issue_opened=True)
        review.publish()

        reply = self.create_reply(review)
        self.create_file_attachment_comment(reply, file_attachment,
                                            reply_to=comment,
                                            issue_opened=True)
        reply.publish()

        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

    def test_save_reply_comment(self):
        """Testing ReviewRequest issue counter and saving reply comments."""
        file_attachment = self.create_file_attachment(self.review_request)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(review, file_attachment,
                                                      issue_opened=True)
        review.publish()

        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        reply = self.create_reply(review)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment,
            reply_to=comment,
            issue_opened=True)
        reply.publish()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        reply_comment.save()
        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 1)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

    def _test_issue_counts(self, create_comment_func):
        review = self.create_review(self.review_request)

        # One comment without an issue opened.
        create_comment_func(review, issue_opened=False)

        # One comment without an issue opened, which will have its
        # status set to a valid status, while closed.
        closed_with_status_comment = \
            create_comment_func(review, issue_opened=False)

        # Three comments with an issue opened.
        for i in range(3):
            create_comment_func(review, issue_opened=True)

        # Two comments that will have their issues dropped.
        dropped_comments = [
            create_comment_func(review, issue_opened=True)
            for i in range(2)
        ]

        # One comment that will have its issue resolved.
        resolved_comments = [
            create_comment_func(review, issue_opened=True)
        ]

        # The issue counts should be end up being 0, since they'll initialize
        # during load.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)
        self.assertEqual(self.review_request.issue_dropped_count, 0)

        # Now publish. We should have 6 open issues, by way of incrementing
        # during publish.
        review.publish()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 6)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

        # Make sure we get the same number back when initializing counters.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 6)
        self.assertEqual(self.review_request.issue_dropped_count, 0)
        self.assertEqual(self.review_request.issue_resolved_count, 0)

        # Set the issue statuses.
        for comment in dropped_comments:
            comment.issue_status = Comment.DROPPED
            comment.save()

        for comment in resolved_comments:
            comment.issue_status = Comment.RESOLVED
            comment.save()

        closed_with_status_comment.issue_status = Comment.OPEN
        closed_with_status_comment.save()

        self._reload_object()
        self.assertEqual(self.review_request.issue_open_count, 3)
        self.assertEqual(self.review_request.issue_dropped_count, 2)
        self.assertEqual(self.review_request.issue_resolved_count, 1)

        # Make sure we get the same number back when initializing counters.
        self._reload_object(clear_counters=True)
        self.assertEqual(self.review_request.issue_open_count, 3)
        self.assertEqual(self.review_request.issue_dropped_count, 2)
        self.assertEqual(self.review_request.issue_resolved_count, 1)

    def _reload_object(self, clear_counters=False):
        if clear_counters:
            # 3 queries: One for the review request fetch, one for
            # the issue status load, and one for updating the issue counts.
            expected_query_count = 3
            self._reset_counts()
        else:
            # One query for the review request fetch.
            expected_query_count = 1

        with self.assertNumQueries(expected_query_count):
            self.review_request = \
                ReviewRequest.objects.get(pk=self.review_request.pk)

    def _reset_counts(self):
        self.review_request.issue_open_count = None
        self.review_request.issue_resolved_count = None
        self.review_request.issue_dropped_count = None
        self.review_request.save()


    fixtures = ['test_users']
        super(PolicyTests, self).setUp()

        self.assertIn(group, Group.objects.accessible(self.user))
        self.assertIn(group, Group.objects.accessible(self.anonymous))
        self.assertNotIn(group, Group.objects.accessible(self.user))
        self.assertNotIn(group, Group.objects.accessible(self.anonymous))
        self.assertIn(group, Group.objects.accessible(self.user))
        self.assertNotIn(group, Group.objects.accessible(self.anonymous))
        """Testing visibility of review requests assigned to invite-only
        groups by a non-member
        """
        review_request = self.create_review_request(publish=True,
                                                    submitter=self.user)
    @add_fixtures(['test_scmtools'])
    @add_fixtures(['test_scmtools'])
    @add_fixtures(['test_scmtools'])
    @add_fixtures(['test_scmtools'])
        """Testing access to a private repository with joined review group
        added
        """
        review_request = self.create_review_request(publish=True)
        """Testing no access to a review request with only an unjoined
        invite-only group
        """
        review_request = self.create_review_request(publish=True)
        """Testing access to a review request with specific target user and
        invite-only group
        """
        review_request = self.create_review_request(publish=True)
    @add_fixtures(['test_scmtools'])
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
    @add_fixtures(['test_scmtools'])
        """Testing access to a review request with a private repository with
        user added
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
    @add_fixtures(['test_scmtools'])
    def test_review_request_with_private_repository_allowed_by_review_group(
            self):
        """Testing access to a review request with a private repository with
        review group added
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
    def test_unicode(self):
        user.first_name = 'Test\u21b9'
        user.last_name = 'User\u2729'


class MarkdownUtilsTests(TestCase):
    UNESCAPED_TEXT = r'\`*_{}[]()#+-.!'
    ESCAPED_TEXT = r'\\\`\*\_\{\}\[\]\(\)#+-.\!'

    def test_get_markdown_element_tree(self):
        """Testing get_markdown_element_tree"""
        node = get_markdown_element_tree(render_markdown('**Test**\nHi.'))

        self.assertEqual(node[0].toxml(),
                         '<p><strong>Test</strong><br/>\n'
                         'Hi.</p>')

    def test_get_markdown_element_tree_with_illegal_chars(self):
        """Testing get_markdown_element_tree with illegal characters"""
        node = get_markdown_element_tree(render_markdown('(**Test**\x0C)'))

        self.assertEqual(node[0].toxml(), '<p>(<strong>Test</strong>)</p>')

    def test_markdown_escape(self):
        """Testing markdown_escape"""
        self.assertEqual(markdown_escape(self.UNESCAPED_TEXT),
                         self.ESCAPED_TEXT)

    def test_markdown_escape_periods(self):
        """Testing markdown_escape with '.' placement"""
        self.assertEqual(
            markdown_escape('Line. 1.\n'
                            '1. Line. 2.\n'
                            '1.2. Line. 3.\n'
                            '  1. Line. 4.'),
            ('Line. 1.\n'
             '1\\. Line. 2.\n'
             '1.2. Line. 3.\n'
             '  1\\. Line. 4.'))

    def test_markdown_escape_atx_headers(self):
        """Testing markdown_escape with '#' placement"""
        self.assertEqual(
            markdown_escape('### Header\n'
                            '  ## Header ##\n'
                            'Not # a header'),
            ('\\#\\#\\# Header\n'
             '  \\#\\# Header ##\n'
             'Not # a header'))

    def test_markdown_escape_hyphens(self):
        """Testing markdown_escape with '-' placement"""
        self.assertEqual(
            markdown_escape('Header\n'
                            '------\n'
                            '\n'
                            '- List item\n'
                            '  - List item\n'
                            'Just hyp-henated'),
            ('Header\n'
             '\\-\\-\\-\\-\\-\\-\n'
             '\n'
             '\\- List item\n'
             '  \\- List item\n'
             'Just hyp-henated'))

    def test_markdown_escape_plusses(self):
        """Testing markdown_escape with '+' placement"""
        self.assertEqual(
            markdown_escape('+ List item\n'
                            'a + b'),
            ('\\+ List item\n'
             'a + b'))

    def test_markdown_escape_underscores(self):
        """Testing markdown_escape with '_' placement"""
        self.assertEqual(markdown_escape('_foo_'), r'\_foo\_')
        self.assertEqual(markdown_escape('__foo__'), r'\_\_foo\_\_')
        self.assertEqual(markdown_escape(' _foo_ '), r' \_foo\_ ')
        self.assertEqual(markdown_escape('f_o_o'), r'f_o_o')
        self.assertEqual(markdown_escape('_f_o_o'), r'\_f_o_o')
        self.assertEqual(markdown_escape('f_o_o_'), r'f_o_o\_')
        self.assertEqual(markdown_escape('foo_ _bar'), r'foo\_ \_bar')
        self.assertEqual(markdown_escape('foo__bar'), r'foo__bar')
        self.assertEqual(markdown_escape('foo\n_bar'), 'foo\n\\_bar')
        self.assertEqual(markdown_escape('(_foo_)'), r'(\_foo\_)')

    def test_markdown_escape_asterisks(self):
        """Testing markdown_escape with '*' placement"""
        self.assertEqual(markdown_escape('*foo*'), r'\*foo\*')
        self.assertEqual(markdown_escape('**foo**'), r'\*\*foo\*\*')
        self.assertEqual(markdown_escape(' *foo* '), r' \*foo\* ')
        self.assertEqual(markdown_escape('f*o*o'), r'f*o*o')
        self.assertEqual(markdown_escape('f*o*o*'), r'f*o*o\*')
        self.assertEqual(markdown_escape('foo* *bar'), r'foo\* \*bar')
        self.assertEqual(markdown_escape('foo**bar'), r'foo**bar')
        self.assertEqual(markdown_escape('foo\n*bar'), 'foo\n\\*bar')

    def test_markdown_escape_parens(self):
        """Testing markdown_escape with '(' and ')' placement"""
        self.assertEqual(markdown_escape('[name](link)'), r'\[name\]\(link\)')
        self.assertEqual(markdown_escape('(link)'), r'(link)')
        self.assertEqual(markdown_escape('](link)'), r'\](link)')
        self.assertEqual(markdown_escape('[foo] ](link)'),
                         r'\[foo\] \](link)')

    def test_markdown_escape_gt_text(self):
        """Testing markdown_escape with '>' for standard text"""
        self.assertEqual(markdown_escape('<foo>'), r'<foo>')

    def test_markdown_escape_gt_blockquotes(self):
        """Testing markdown_escape with '>' for blockquotes"""
        self.assertEqual(markdown_escape('>'), r'\>')
        self.assertEqual(markdown_escape('> foo'), r'\> foo')
        self.assertEqual(markdown_escape('  > foo'), r'  \> foo')
        self.assertEqual(markdown_escape('> > foo'), r'\> \> foo')
        self.assertEqual(markdown_escape('  > > foo'), r'  \> \> foo')

    def test_markdown_escape_gt_autolinks(self):
        """Testing markdown_escape with '>' for autolinks"""
        self.assertEqual(markdown_escape('<http://www.example.com>'),
                         r'<http://www.example.com\>')

    def test_markdown_escape_gt_autoemail(self):
        """Testing markdown_escape with '>' for autoemails"""
        self.assertEqual(markdown_escape('<user@example.com>'),
                         r'<user@example.com\>')

    def test_markdown_unescape(self):
        """Testing markdown_unescape"""
        self.assertEqual(markdown_unescape(self.ESCAPED_TEXT),
                         self.UNESCAPED_TEXT)

        self.assertEqual(
            markdown_unescape('&nbsp;   code\n'
                              '&nbsp;   code'),
            ('    code\n'
             '    code'))
        self.assertEqual(
            markdown_unescape('&nbsp;\tcode\n'
                              '&nbsp;\tcode'),
            ('\tcode\n'
             '\tcode'))

    def test_normalize_text_for_edit_rich_text_default_rich_text(self):
        """Testing normalize_text_for_edit with rich text and
        user defaults to rich text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=True)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True)
        self.assertEqual(text, '&amp;lt; &quot;test&quot; **foo**')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_plain_text_default_rich_text(self):
        """Testing normalize_text_for_edit with plain text and
        user defaults to rich text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=True)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=False)
        self.assertEqual(text, r'&amp;lt; &quot;test&quot; \*\*foo\*\*')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_rich_text_default_plain_text(self):
        """Testing normalize_text_for_edit with rich text and
        user defaults to plain text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True)
        self.assertEqual(text, '&amp;lt; &quot;test&quot; **foo**')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_plain_text_default_plain_text(self):
        """Testing normalize_text_for_edit with plain text and
        user defaults to plain text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True)
        self.assertEqual(text, '&amp;lt; &quot;test&quot; **foo**')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_rich_text_no_escape(self):
        """Testing normalize_text_for_edit with rich text and not
        escaping to HTML
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True, escape_html=False)
        self.assertEqual(text, '&lt; "test" **foo**')
        self.assertFalse(isinstance(text, SafeText))

    def test_normalize_text_for_edit_plain_text_no_escape(self):
        """Testing normalize_text_for_edit with plain text and not
        escaping to HTML
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True, escape_html=False)
        self.assertEqual(text, '&lt; "test" **foo**')
        self.assertFalse(isinstance(text, SafeText))


class MarkdownRenderTests(TestCase):
    """Unit tests for Markdown rendering."""
    def test_code_1_blank_line(self):
        """Testing Markdown rendering with code block and 1 surrounding blank
        line
        """
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<div class="codehilite"><pre>if (1) {}\n'
             '</pre></div>\n'
             '<p>done.</p>'))

    def test_code_2_blank_lines(self):
        """Testing Markdown rendering with code block and 2 surrounding blank
        lines
        """
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<div class="codehilite"><pre>if (1) {}\n'
             '</pre></div>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_code_3_blank_lines(self):
        """Testing Markdown rendering with code block and 3 surrounding blank
        lines
        """
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<div class="codehilite"><pre>if (1) {}\n'
             '</pre></div>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_code_4_blank_lines(self):
        """Testing Markdown rendering with code block and 4 surrounding blank
        lines
        """
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '\n'
                '\n'
                '    if (1) {}\n'
                '\n'
                '\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<div class="codehilite"><pre>if (1) {}\n'
             '</pre></div>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_lists_1_blank_line(self):
        """Testing Markdown rendering with 1 blank lines between lists"""
        # This really just results in a single list. This is Python Markdown
        # behavior.
        self.assertEqual(
            render_markdown(
                '1. item\n'
                '\n'
                '1. item'),
            ('<ol>\n'
             '<li>\n'
             '<p>item</p>\n'
             '</li>\n'
             '<li>\n'
             '<p>item</p>\n'
             '</li>\n'
             '</ol>'))

    def test_lists_2_blank_line(self):
        """Testing Markdown rendering with 2 blank lines between lists"""
        self.assertEqual(
            render_markdown(
                '1. item\n'
                '\n'
                '\n'
                '1. item'),
            ('<ol>\n'
             '<li>item</li>\n'
             '</ol>\n'
             '<p></p>\n'
             '<ol>\n'
             '<li>item</li>\n'
             '</ol>'))

    def test_lists_3_blank_line(self):
        """Testing Markdown rendering with 3 blank lines between lists"""
        self.assertEqual(
            render_markdown(
                '1. item\n'
                '\n'
                '\n'
                '\n'
                '1. item'),
            ('<ol>\n'
             '<li>item</li>\n'
             '</ol>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<ol>\n'
             '<li>item</li>\n'
             '</ol>'))

    def test_ol(self):
        """Testing Markdown rendering with ordered lists"""
        self.assertEqual(
            render_markdown(
                '1. Foo\n'
                '2. Bar'),
            ('<ol>\n'
             '<li>Foo</li>\n'
             '<li>Bar</li>\n'
             '</ol>'))

    def test_ol_start(self):
        """Testing Markdown rendering with ordered lists using start="""
        self.assertEqual(
            render_markdown(
                '5. Foo\n'
                '6. Bar'),
            ('<ol start="5" style="counter-reset: li 4">\n'
             '<li>Foo</li>\n'
             '<li>Bar</li>\n'
             '</ol>'))

    def test_text_0_blank_lines(self):
        """Testing Markdown rendering with 0 blank lines between text"""
        self.assertEqual(
            render_markdown(
                'begin:\n'
                'done.'),
            ('<p>begin:<br />\n'
             'done.</p>'))

    def test_text_1_blank_line(self):
        """Testing Markdown rendering with 1 blank line between text"""
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p>done.</p>'))

    def test_text_2_blank_lines(self):
        """Testing Markdown rendering with 2 blank lines between text"""
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_text_3_blank_lines(self):
        """Testing Markdown rendering with 3 blank lines between text"""
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '\n'
                '\n'
                'done.'),
            ('<p>begin:</p>\n'
             '<p></p>\n'
             '<p></p>\n'
             '<p>done.</p>'))

    def test_trailing_p_trimmed(self):
        """Testing Markdown rendering trims trailing paragraphs"""
        self.assertEqual(
            render_markdown(
                'begin:\n'
                '\n'
                '\n'),
            '<p>begin:</p>')


class MarkdownTemplateTagsTests(TestCase):
    """Unit tests for Markdown-related template tags."""
    def setUp(self):
        super(MarkdownTemplateTagsTests, self).setUp()

        self.user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=self.user, default_use_rich_text=False)

        request_factory = RequestFactory()
        request = request_factory.get('/')

        request.user = self.user
        self.context = Context({
            'request': request,
        })

    def test_normalize_text_for_edit_escape_html(self):
        """Testing {% normalize_text_for_edit %} escaping for HTML"""
        t = Template(
            "{% load reviewtags %}"
            "{% normalize_text_for_edit '&lt;foo **bar**' True %}")

        self.assertEqual(t.render(self.context), '&amp;lt;foo **bar**')

    def test_normalize_text_for_edit_escaping_js(self):
        """Testing {% normalize_text_for_edit %} escaping for JavaScript"""
        t = Template(
            "{% load reviewtags %}"
            "{% normalize_text_for_edit '&lt;foo **bar**' True True %}")

        self.assertEqual(t.render(self.context),
                         '\\u0026lt\\u003Bfoo **bar**')

    def test_sanitize_illegal_chars(self):
        """Testing sanitize_illegal_chars_for_xml"""
        s = '<a>\u2018\u2019\u201c\u201d\u201c\u201d</a>'

        # This used to cause a UnicodeDecodeError
        nodes = get_markdown_element_tree(s)

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].toxml(),
                         '<a>\u2018\u2019\u201c\u201d\u201c\u201d</a>')


class InitReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/jpg']

    def __init__(self, review_request, obj):
        raise Exception


class SandboxReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/png']

    def is_enabled_for(self, user=None, review_request=None,
                       file_attachment=None, **kwargs):
        raise Exception

    def get_comment_thumbnail(self, comment):
        raise Exception

    def get_comment_link_url(self, comment):
        raise Exception

    def get_comment_link_text(self, comment):
        raise Exception

    def get_extra_context(self, request):
        raise Exception

    def get_js_view_data(self):
        raise Exception

    def serialize_comments(self, comments):
        raise Exception


class ConflictFreeReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/gif']

    def serialize_comment(self, comment):
        raise Exception

    def get_js_model_data(self):
        raise Exception


class SandboxTests(SpyAgency, TestCase):
    """Testing sandboxing extensions."""
    fixtures = ['test_users']

    def setUp(self):
        super(SandboxTests, self).setUp()

        register_ui(InitReviewUI)
        register_ui(SandboxReviewUI)
        register_ui(ConflictFreeReviewUI)

        self.factory = RequestFactory()

        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'trophy.png')

        with open(filename, 'r') as f:
            self.file = SimpleUploadedFile(f.name, f.read(),
                                           content_type='image/png')

        self.user = User.objects.get(username='doc')
        self.review_request = ReviewRequest.objects.create(self.user, None)
        self.file_attachment1 = FileAttachment.objects.create(
            mimetype='image/jpg',
            file=self.file)
        self.file_attachment2 = FileAttachment.objects.create(
            mimetype='image/png',
            file=self.file)
        self.file_attachment3 = FileAttachment.objects.create(
            mimetype='image/gif',
            file=self.file)
        self.review_request.file_attachments.add(self.file_attachment1)
        self.review_request.file_attachments.add(self.file_attachment2)
        self.review_request.file_attachments.add(self.file_attachment3)
        self.draft = ReviewRequestDraft.create(self.review_request)

    def tearDown(self):
        super(SandboxTests, self).tearDown()

        unregister_ui(InitReviewUI)
        unregister_ui(SandboxReviewUI)
        unregister_ui(ConflictFreeReviewUI)

    def test_init_review_ui(self):
        """Testing FileAttachmentReviewUI sandboxes for __init__"""
        self.spy_on(InitReviewUI.__init__)

        self.file_attachment1.review_ui

        self.assertTrue(InitReviewUI.__init__.called)

    def test_is_enabled_for(self):
        """Testing FileAttachmentReviewUI sandboxes for
        is_enabled_for
        """
        comment = "Comment"

        self.spy_on(SandboxReviewUI.is_enabled_for)

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/' % self.review_request.pk)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(SandboxReviewUI.is_enabled_for.called)

    def test_get_comment_thumbnail(self):
        """Testing FileAttachmentReviewUI sandboxes for
        get_comment_thumbnail
        """
        comment = "Comment"

        review_ui = self.file_attachment2.review_ui

        self.spy_on(review_ui.get_comment_thumbnail)

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        file_attachment_comments = review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        file_attachment_comments.thumbnail

        self.assertTrue(review_ui.get_comment_thumbnail.called)

    def test_get_comment_link_url(self):
        """Testing FileAttachmentReviewUI sandboxes for get_comment_link_url"""
        comment = "Comment"

        review_ui = self.file_attachment2.review_ui

        self.spy_on(review_ui.get_comment_link_url)

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        file_attachment_comments = review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        file_attachment_comments.get_absolute_url()

        self.assertTrue(review_ui.get_comment_link_url.called)

    def test_get_comment_link_text(self):
        """Testing FileAttachmentReviewUI sandboxes for
        get_comment_link_text
        """
        comment = "Comment"

        review_ui = self.file_attachment2.review_ui

        self.spy_on(review_ui.get_comment_link_text)

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        file_attachment_comments = review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        file_attachment_comments.get_link_text()

        self.assertTrue(review_ui.get_comment_link_text.called)

    def test_get_extra_context(self):
        """Testing FileAttachmentReviewUI sandboxes for
        get_extra_context
        """
        review_ui = self.file_attachment2.review_ui
        request = self.factory.get('test')
        request.user = self.user

        self.spy_on(review_ui.get_extra_context)

        review_ui.render_to_string(request=request)

        self.assertTrue(review_ui.get_extra_context.called)

    def test_get_js_model_data(self):
        """Testing FileAttachmentReviewUI sandboxes for
        get_js_model_data
        """
        review_ui = self.file_attachment3.review_ui
        request = self.factory.get('test')
        request.user = self.user

        self.spy_on(review_ui.get_js_model_data)

        review_ui.render_to_response(request=request)

        self.assertTrue(review_ui.get_js_model_data.called)

    def test_get_js_view_data(self):
        """Testing FileAttachmentReviewUI sandboxes for
        get_js_view_data
        """
        review_ui = self.file_attachment2.review_ui
        request = self.factory.get('test')
        request.user = self.user

        self.spy_on(review_ui.get_js_view_data)

        review_ui.render_to_response(request=request)

        self.assertTrue(review_ui.get_js_view_data.called)

    def test_serialize_comments(self):
        """Testing FileAttachmentReviewUI sandboxes for
        serialize_comments
        """
        review_ui = self.file_attachment2.review_ui

        self.spy_on(review_ui.serialize_comments)

        review_ui.get_comments_json()

        self.assertTrue(review_ui.serialize_comments.called)

    def test_serialize_comment(self):
        """Testing FileAttachmentReviewUI sandboxes for
        serialize_comment
        """
        comment = 'comment'

        review_ui = self.file_attachment3.review_ui
        request = self.factory.get('test')
        request.user = self.user
        review_ui.request = request

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user, public=True)
        file_attachment_comments = review.file_attachment_comments.create(
            file_attachment=self.file_attachment3,
            text=comment)

        self.spy_on(review_ui.serialize_comment)

        serial_comments = review_ui.serialize_comments(
            comments=[file_attachment_comments])
        self.assertRaises(StopIteration, next, serial_comments)

        self.assertTrue(review_ui.serialize_comment.called)