"""
"""
import random
from locust import HttpLocust, TaskSet, task

import settings


def client_is_logged_into_edx(client):
    return client.cookies.get('edxloggedin') == 'true'


class ProblemSubmission(TaskSet):
    """
    """
    course_data = None

    def on_start(self):
        """on_start is called before any task is scheduled """
        self.course_data = self.parent.course_data

    @staticmethod
    def _get_answer_post_url(course_id, block_id):
        return '/courses/{}/xblock/{}/handler/xmodule_handler/problem_check'.format(
            course_id,
            block_id
        )

    @staticmethod
    def _answer_post_dict(choicegroup_id, answer_id):
        return {'input_{}'.format(choicegroup_id): answer_id}

    @task
    def submit_answer(self):
        """
        """
        # Stop this task if not logged in yet
        if not client_is_logged_into_edx(self.client):
            self.interrupt()
        course_id = self.course_data['course_id']
        block = random.choice(self.course_data['blocks'])
        block_id = block['id']
        choicegroup_id = block['choicegroup_id']
        answer_id = random.choice(block['answer_ids'])
        self.client.post(
            self._get_answer_post_url(course_id, block_id),
            data=self._answer_post_dict(choicegroup_id, answer_id),
            headers={
                'X-CSRFToken': self.client.cookies.get('csrftoken')
            },
            name='Problem Submission',
        )

    @task
    def stop(self):
        self.interrupt()


class UserLogIn(TaskSet):
    """
    """
    tasks = {ProblemSubmission: 5}
    enrolled_users = None
    username = None
    course_data = None
    pw = 'edx'

    def on_start(self):
        """on_start is called before any task is scheduled """
        self.enrolled_users = self.parent.enrolled_users
        self.username = random.choice(settings.USERNAMES_IN_EDX)
        self.course_data = random.choice(settings.RAPID_RESPONSE_COURSE_DATA)

    def _login(self):
        # load the login form to get the token
        initial_login_resp = self.client.get(
            '/login',
            name='Initial login request'
        )
        csrf_token = initial_login_resp.cookies.get('csrftoken')
        # login edx
        self.client.post(
            '/user_api/v1/account/login_session/',
            data={
                'email': '{}@example.com'.format(self.username),
                'password': self.pw,
                'remember': 'false'
            },
            headers={
                'Referer': '/login',
                'X-CSRFToken': csrf_token
            },
            name='Actual login'
        )

    def _enroll(self):
        course_id = self.course_data['course_id']
        # Unenrolling before enrolling because edX throws an error when an enrolled
        # user requests to enroll again.
        for enrollment_action in ['unenroll', 'enroll']:
            self.client.post(
                '/change_enrollment',
                data={
                    'course_id': course_id,
                    'enrollment_action': enrollment_action
                },
                headers={
                    'X-CSRFToken': self.client.cookies.get('csrftoken')
                },
                name='Course Enrollment ({})'.format(enrollment_action),
            )
        self.enrolled_users.add(self.username)

    @task
    def login_and_enroll(self):
        """
        """
        if not client_is_logged_into_edx(self.client):
            self._login()
        if not self.username in self.enrolled_users:
            self._enroll()

    @task
    def stop(self):
        self.interrupt()


class UserBehavior(TaskSet):
    tasks = [UserLogIn]
    enrolled_users = set()


class WebsiteUser(HttpLocust):
    host = settings.LMS_BASE_URL
    task_set = UserBehavior
    min_wait = settings.LOCUST_TASK_MIN_WAIT
    max_wait = settings.LOCUST_TASK_MAX_WAIT


if __name__ == "__main__":
    WebsiteUser().run()
