"""
Tests for ORA (Open Response Assessment) through the LMS UI.
"""

import json
from bok_choy.promise import fulfill, Promise
from ..pages.studio.auto_auth import AutoAuthPage
from ..pages.lms.course_info import CourseInfoPage
from ..pages.lms.tab_nav import TabNavPage
from ..pages.lms.course_nav import CourseNavPage
from ..pages.lms.open_response import OpenResponsePage
from ..pages.lms.progress import ProgressPage
from ..fixtures.course import XBlockFixtureDesc, CourseFixture
from ..fixtures.xqueue import XQueueResponseFixture

from .helpers import load_data_str, UniqueCourseTest


class OpenResponseTest(UniqueCourseTest):
    """
    Tests that interact with ORA (Open Response Assessment) through the LMS UI.
    This base class sets up a course with open response problems and defines
    some helper functions used in the ORA tests.
    """

    # Grade response (dict) to return from the XQueue stub
    # in response to our unique submission text.
    XQUEUE_GRADE_RESPONSE = None

    def setUp(self):
        """
        Install a test course with ORA problems.
        Always start in the subsection with open response problems.
        """
        super(OpenResponseTest, self).setUp()

        # Create page objects
        self.auth_page = AutoAuthPage(self.browser, course_id=self.course_id)
        self.course_info_page = CourseInfoPage(self.browser, self.course_id)
        self.tab_nav = TabNavPage(self.browser)
        self.course_nav = CourseNavPage(self.browser)
        self.open_response = OpenResponsePage(self.browser)
        self.progress_page = ProgressPage(self.browser, self.course_id)

        # Configure the test course
        course_fix = CourseFixture(
            self.course_info['org'], self.course_info['number'],
            self.course_info['run'], self.course_info['display_name']
        )

        course_fix.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(

                    XBlockFixtureDesc('combinedopenended', 'Self-Assessed',
                        data=load_data_str('ora_self_problem.xml'), metadata={'graded': True}),

                    XBlockFixtureDesc('combinedopenended', 'AI-Assessed',
                        data=load_data_str('ora_ai_problem.xml'), metadata={'graded': True}),

                    XBlockFixtureDesc('combinedopenended', 'Peer-Assessed',
                        data=load_data_str('ora_peer_problem.xml'), metadata={'graded': True}),

                    XBlockFixtureDesc('peergrading', 'Peer Module'),

        ))).install()

        # Configure the XQueue stub's response for the text we will submit
        # The submission text is unique so we can associate each response with a particular test case.
        self.submission = "Test submission " + self.unique_id[0:4]
        if self.XQUEUE_GRADE_RESPONSE is not None:
            XQueueResponseFixture(self.submission, self.XQUEUE_GRADE_RESPONSE).install()

        # Log in and navigate to the essay problems
        self.auth_page.visit()
        self.course_info_page.visit()
        self.tab_nav.go_to_tab('Courseware')

    def submit_essay(self, expected_assessment_type, expected_prompt):
        """
        Submit an essay and verify that the problem uses
        the `expected_assessment_type` ("self", "ai", or "peer") and
        shows the `expected_prompt` (a string).
        """

        # Check the assessment type and prompt
        self.assertEqual(self.open_response.assessment_type, expected_assessment_type)
        self.assertIn(expected_prompt, self.open_response.prompt)

        # Enter a submission, which will trigger a pre-defined response from the XQueue stub.
        self.open_response.set_response(self.submission)

        # Save the response and expect some UI feedback
        self.open_response.save_response()
        self.assertEqual(
            self.open_response.alert_message,
            "Answer saved, but not yet submitted."
        )

        # Submit the response
        self.open_response.submit_response()

    def get_asynch_feedback(self, assessment_type):
        """
        Wait for and retrieve asynchronous feedback
        (e.g. from AI, instructor, or peer grading)
        `assessment_type` is either "ai" or "peer".
        """
        # Because the check function involves fairly complicated actions
        # (navigating through several screens), we give it more time to complete
        # than the default.
        feedback_promise = Promise(
            self._check_feedback_func(assessment_type),
            'Got feedback for {0} problem'.format(assessment_type),
            timeout=600, try_interval=5
        )
        return fulfill(feedback_promise)

    def _check_feedback_func(self, assessment_type):
        """
        Navigate away from, then return to, the peer problem to
        receive updated feedback.

        The returned function will return a tuple `(is_success, rubric_feedback)`,
        `is_success` is True iff we have received feedback for the problem;
        `rubric_feedback` is a list of "correct" or "incorrect" strings.
        """
        if assessment_type == 'ai':
            section_name = 'AI-Assessed'
        elif assessment_type == 'peer':
            section_name = 'Peer-Assessed'
        else:
            raise ValueError('Assessment type not recognized.  Must be either "ai" or "peer"')

        def _inner_check():
            self.course_nav.go_to_sequential('Self-Assessed')
            self.course_nav.go_to_sequential(section_name)
            feedback = self.open_response.rubric_feedback

            # Successful if `feedback` is a non-empty list
            return (bool(feedback), feedback)

        return _inner_check


class SelfAssessmentTest(OpenResponseTest):
    """
    Test ORA self-assessment.
    """

    def test_self_assessment(self):
        """
        Given I am viewing a self-assessment problem
        When I submit an essay and complete a self-assessment rubric
        Then I see a scored rubric
        And I see my score in the progress page.
        """
        # Navigate to the self-assessment problem and submit an essay
        self.course_nav.go_to_sequential('Self-Assessed')
        self.submit_essay('self', 'Censorship in the Libraries')

        # Check the rubric categories
        self.assertEqual(
            self.open_response.rubric_categories, ["Writing Applications", "Language Conventions"]
        )

        # Fill in the self-assessment rubric
        self.open_response.submit_self_assessment([0, 1])

        # Expect that we get feedback
        self.assertEqual(
            self.open_response.rubric_feedback, ['incorrect', 'correct']
        )

        # Verify the progress page
        self.progress_page.visit()
        scores = self.progress_page.scores('Test Section', 'Test Subsection')

        # The first score is self-assessment, which we've answered, so it's 1/2
        # The other scores are AI- and peer-assessment, which we haven't answered so those are 0/2
        self.assertEqual(scores, [(1, 2), (0, 2), (0, 2)])


class AIAssessmentTest(OpenResponseTest):
    """
    Test ORA AI-assessment.
    """

    XQUEUE_GRADE_RESPONSE = {
        'score': 1,
        'feedback': {"spelling": "Ok.", "grammar": "Ok.", "markup_text": "NA"},
        'grader_type': 'BC',
        'success': True,
        'grader_id': 1,
        'submission_id': 1,
        'rubric_scores_complete': True,
        'rubric_xml': load_data_str('ora_rubric.xml')
    }

    def test_ai_assessment(self):
        """
        Given I am viewing an AI-assessment problem that has a trained ML model
        When I submit an essay and wait for a response
        Then I see a scored rubric
        And I see my score in the progress page.
        """

        # Navigate to the AI-assessment problem and submit an essay
        self.course_nav.go_to_sequential('AI-Assessed')
        self.submit_essay('ai', 'Censorship in the Libraries')

        # Refresh the page to get the updated feedback
        # then verify that we get the feedback sent by our stub XQueue implementation
        self.assertEqual(self.get_asynch_feedback('ai'), ['incorrect', 'correct'])

        # Verify the progress page
        self.progress_page.visit()
        scores = self.progress_page.scores('Test Section', 'Test Subsection')

        # First score is the self-assessment score, which we haven't answered, so it's 0/2
        # Second score is the AI-assessment score, which we have answered, so it's 1/2
        # Third score is peer-assessment, which we haven't answered, so it's 0/2
        self.assertEqual(scores, [(0, 2), (1, 2), (0, 2)])


class InstructorAssessmentTest(AIAssessmentTest):
    """
    Test an AI-assessment that has been graded by an instructor.
    This runs the exact same test as the AI-assessment test, except
    that the feedback comes from an instructor instead of the machine grader.
    From the student's perspective, it should look the same.
    """

    XQUEUE_GRADE_RESPONSE = {
        'score': 1,
        'feedback': {"feedback": "Good job!"},
        'grader_type': 'IN',
        'success': True,
        'grader_id': 1,
        'submission_id': 1,
        'rubric_scores_complete': True,
        'rubric_xml': load_data_str('ora_rubric.xml')
    }


class PeerFeedbackTest(OpenResponseTest):
    """
    Test ORA peer-assessment.  Note that this tests only *receiving* feedback,
    not *giving* feedback -- those tests are located in another module.
    """

    # Unlike other assessment types, peer assessment has multiple scores
    XQUEUE_GRADE_RESPONSE = {
        'score': [2, 2, 2],
        'feedback': [json.dumps({"feedback": ""})] * 3,
        'grader_type': 'PE',
        'success': True,
        'grader_id': [1, 2, 3],
        'submission_id': 1,
        'rubric_scores_complete': [True, True, True],
        'rubric_xml': [load_data_str('ora_rubric.xml')] * 3
    }

    def test_peer_assessment(self):
        """
        Given I have submitted an essay for peer-assessment
        And enough other students have scored my essay
        Then I can view the scores and written feedback
        And I see my score in the progress page.
        """
        # Navigate to the peer-assessment problem and submit an essay
        self.course_nav.go_to_sequential('Peer-Assessed')
        self.submit_essay('peer', 'Censorship in the Libraries')

        # Refresh the page to get feedback from the stub XQueue grader.
        # We receive feedback from all three peers, each of which
        # provide 2 scores (one for each rubric item)
        self.assertEqual(self.get_asynch_feedback('peer'), ['incorrect', 'correct'] * 3)

        # Verify the progress page
        self.progress_page.visit()
        scores = self.progress_page.scores('Test Section', 'Test Subsection')

        # First score is the self-assessment score, which we haven't answered, so it's 0/2
        # Second score is the AI-assessment score, which we haven't answered, so it's 0/2
        # Third score is peer-assessment, which we have answered, so it's 2/2
        self.assertEqual(scores, [(0, 2), (0, 2), (2, 2)])
