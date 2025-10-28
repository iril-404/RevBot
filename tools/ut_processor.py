import re
import os
import requests
from dotenv import load_dotenv

from configs.config import GITHUB_URL, PROJECT_MAPPING, ENV_PATH, LIB_PATH

class UTProcessor:
    def __init__(
            self,
            owner: str,
        ):
        
        self.owner = owner

        self.save_folder = os.path.join(LIB_PATH, self.owner, 'ut')

        self.token = os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()

        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
    def processor(self):
        repo_list = PROJECT_MAPPING[self.owner]['Repo']  # repo list

        for repo in repo_list:
            url = f"{GITHUB_URL}/api/v3/repos/{self.owner}/{repo}"
            branch = self._get_default_branch(url)

            files = self._list_files_recursively(repo=repo, branch=branch)
            test_files = [f for f in files if f.endswith(".test")]

            save_folder = os.path.join(self.save_folder, repo)
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)

            for file_path in test_files:
                self._download_file(repo, file_path, branch, save_folder)

    def _get_default_branch(self, url):
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            resp = self.session.get(url, headers=headers)
            resp.raise_for_status()

            default_branch = resp.json().get("default_branch")
            
            return default_branch

        except Exception as e:
            print(f"请求失败，状态码：{resp.status_code}，内容：{resp.text}")

            return None
    
    def _list_files_recursively(self, repo, branch):
        url = f"{GITHUB_URL}/api/v3/repos/{self.owner}/{repo}/git/trees/{branch}?recursive=1"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return [item["path"] for item in resp.json()["tree"] if item["type"] == "blob"]

    def _download_file(self, repo, file_path, branch, save_folder):
        raw_url = f"{GITHUB_URL}/api/v3/repos/{self.owner}/{repo}/contents/{file_path}?ref={branch}"
        resp = requests.get(raw_url, headers=self.headers)
        resp.raise_for_status()
        file_content = requests.get(resp.json()["download_url"]).content

        filename = os.path.basename(file_path) 

        local_path = os.path.join(save_folder, filename)

        with open(local_path, "wb") as f:
            f.write(file_content)



if __name__ == '__main__':
    load_dotenv(ENV_PATH)

    qp = UTProcessor(owner = 'gee-crx-24-zcu')
    qp.processor()
