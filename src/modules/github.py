import requests
import re
import logging

from configs.config import GITHUB_URL

class GithubPROps:
    """
    Handles GitHub PR operations, such as fetching PR diff and extracting Jira ticket.
    """
    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.session = requests.Session()
        escaped_url = GITHUB_URL.replace('.', '\\.')
        self.pr_url_pattern = re.compile(rf"{escaped_url}/([^/]+)/([^/]+)/pull/(\d+)")
        if self.username and self.password:
            self.session.auth = (self.username, self.password)
        self.logger = logging.getLogger(__name__)

    def parse_pr_url(self, pr_url: str):
        """
        Parse PR URL and return (owner, repo, pr_number). Raise ValueError if format is incorrect.
        """
        m = self.pr_url_pattern.match(pr_url)
        if not m:
            self.logger.error("PR link format is incorrect, cannot extract repository info")
        return m.group(1), m.group(2), m.group(3)

    def _get_api_url(self, pr_url: str) -> str:
        owner, repo, pr_number = self.parse_pr_url(pr_url)
        api_url = f"{GITHUB_URL}/api/v3/repos/{owner}/{repo}/pulls/{pr_number}"
        return api_url

    def get_pr_diff(self, pr_url: str) -> str:
        api_url = self._get_api_url(pr_url)
        headers = {"Accept": "application/vnd.github.v3.diff"}
        resp = self.session.get(api_url, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.text

    def get_pr_changed_files(self, pr_url: str) -> list:
        owner, repo, pr_number = self.parse_pr_url(pr_url)
        files_api_url = f"{GITHUB_URL}/api/v3/repos/{owner}/{repo}/pulls/{pr_number}/files"
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = self.session.get(files_api_url, headers=headers, timeout=60)
        resp.raise_for_status()
        files_data = resp.json()

        changed_files = [f["filename"] for f in files_data]
        return changed_files

    def create_pr_comment(self, pr_url: str, body: str) -> None:
        """
        Write a comment under the specified PR. If the current account already has a comment, update the original comment, otherwise create a new one.
        """
        owner, repo, pr_number = self.parse_pr_url(pr_url)
        comments_url = f"{GITHUB_URL}/api/v3/repos/{owner}/{repo}/issues/{pr_number}/comments"
        headers = {"Accept": "application/vnd.github.v3+json"}
        # 1. Get all comments
        resp = self.session.get(comments_url, headers=headers, timeout=60)
        resp.raise_for_status()
        comments = resp.json()
        my_comment = None
        for c in comments:
            if c.get("user", {}).get("login", "").lower() == self.username.lower():
                my_comment = c
                break
        if my_comment:
            # 2. Already has comment, update
            comment_id = my_comment["id"]
            patch_url = f"{GITHUB_URL}/api/v3/repos/{owner}/{repo}/issues/comments/{comment_id}"
            patch_data = {"body": body}
            patch_resp = self.session.patch(patch_url, json=patch_data, headers=headers, timeout=10)
            patch_resp.raise_for_status()
        else:
            # 3. Otherwise create new
            data = {"body": body}
            post_resp = self.session.post(comments_url, json=data, headers=headers, timeout=10)
            post_resp.raise_for_status()

    def get_pr_info(self, pr_url: str):
        api_url = self._get_api_url(pr_url)
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = self.session.get(api_url, headers=headers, timeout=60)
        resp.raise_for_status()
        pr_data = resp.json()
        pr_title = pr_data.get("title")
        source_branch = pr_data.get("head", {}).get("ref", "")
        base_branch = pr_data.get("base", {}).get("ref", "")
        match = re.match(r"feature/([^/]+)*", source_branch)
        if match:
            jira_ticket = match.group(1)
        else:
            jira_ticket = source_branch
        
        return jira_ticket, base_branch, pr_title

    def get_pr_filter_diff(self, diff_text, exclude_exts):
        diff_chunks = re.split(r'(?=^diff --git )', diff_text, flags=re.MULTILINE)

        filtered_chunks = []
        for chunk in diff_chunks:
            if not chunk.strip():
                continue

            first_line = chunk.split('\n', 1)[0]
            
            try:
                file_path_b = first_line.split(' ')[2]
            except IndexError:
                filtered_chunks.append(chunk)
                continue
            
            is_excluded = any(file_path_b.endswith(ext) for ext in exclude_exts)

            if not is_excluded:
                filtered_chunks.append(chunk)

        return "".join(filtered_chunks)
    