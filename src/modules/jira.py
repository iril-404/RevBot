import requests
import logging

from configs.config import JIRA_URL

class JiraApi:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.logger = logging.getLogger(__name__)

    def get_summary(self, issue_key):
        url = f"{JIRA_URL}rest/api/latest/issue/{issue_key}"
        resp = self.session.get(url)
        if resp.ok:
            return resp.json().get('fields', {}).get('summary')
        else:
            self.logger.error(f"Failed to get summary")
            return None
