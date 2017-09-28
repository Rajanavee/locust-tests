"""
locust file for open discussions
This tests the user addition to open_discussions

This needs to be run with maximum 10 locust users
we are simulating the micromasters dynos batch creating users on OD, not real uses using the system
"""
import random

from faker import Faker
from locust import HttpLocust, TaskSet, task
from open_discussions_api.client import OpenDiscussionsApi
from open_discussions_api.users.client import UsersApi, SUPPORTED_USER_ATTRIBUTES, quote

import settings


fake = Faker()


def patch_get_session(client):
    """
    Monkey patch the get session of OpenDiscussionApi to use the locust client
    """
    def patched_func(self):
        return client
    return patched_func


def patched_user_update(self, username, **profile):
    """
    Monkey patch the user update
    """
    if not profile:
        raise AttributeError("No fields provided to update")

    for key in profile:
        if key not in SUPPORTED_USER_ATTRIBUTES:
            raise AttributeError("Argument {} is not supported".format(key))

    return self.session.patch(
        self.get_url("/users/{}/".format(quote(username))),
        json=dict(profile=profile),
        name="/users/[username]/",
    )


class UserCreation(TaskSet):

    tasks = {}
    discussion_usernames_number = 100

    def on_start(self):
        """on_start is called before any task is scheduled """
        self.discussion_usernames = []

        # monkey patch the library client
        OpenDiscussionsApi._get_session = patch_get_session(self.client)
        UsersApi.update = patched_user_update

        self.api = OpenDiscussionsApi(
            settings.OPEN_DISCUSSIONS_JWT_SECRET,
            settings.OPEN_DISCUSSIONS_BASE_URL,
            settings.OPEN_DISCUSSIONS_API_USERNAME,
            roles=['staff']
        )

    @task
    def create_users(self):
        """creates the users in the system"""
        # limit the number of users
        if len(self.discussion_usernames) >= self.discussion_usernames_number:
            return
        res = self.api.users.create(name=fake.name(), image=None, image_small=None, image_medium=None)
        if res.status_code == 201:
            self.discussion_usernames.append(res.json()['username'])

    @task
    def update_users(self):
        """updates the users in the system"""
        # try to get the user
        if not len(self.discussion_usernames):
            return
        self.api.users.update(
            username=random.choice(self.discussion_usernames),
            name=fake.name(),
            image=None,
            image_small=None,
            image_medium=None
        )


class WebsiteUser(HttpLocust):
    host = settings.OPEN_DISCUSSIONS_BASE_URL
    task_set = UserCreation
    # this is simulating requests from celery tasks, so very low wait between the different requests
    min_wait = 1
    max_wait = 100
