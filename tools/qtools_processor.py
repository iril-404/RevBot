import re
import os
import requests
from dotenv import load_dotenv
import pickle

from configs.config import GITHUB_URL, PROJECT_MAPPING, ENV_PATH, LIB_PATH

class QtoolsProcessor:
    def __init__(
            self,
            owner: str,
        ):
        
        self.owner = owner

        self.save_folder = os.path.join(LIB_PATH, self.owner, 'qtools')

        self.token = os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
    
    def processor(self):
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)

        repo_list = PROJECT_MAPPING[self.owner]['Repo']  # repo list
        qtools_cfg_url_list = PROJECT_MAPPING[self.owner]['Qtools_path']

        for (repo, qtools_cfg_url) in zip(repo_list, qtools_cfg_url_list):
            url = f"{GITHUB_URL}/api/v3/repos/{self.owner}/{repo}"
            branch = self._get_default_branch(url)

            url = f"{GITHUB_URL}/api/v3/repos/{self.owner}/{repo}/contents/{qtools_cfg_url}?ref={branch}"

            save_file_path = self._download_qtools_cfg(url, repo)  # download qtools cfg to local folder

            if save_file_path:
                self._convert_cfg_to_dict(save_file_path)
    
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
        
    def _download_qtools_cfg(self, url, repo):
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.raw+json"
        }

        try:
            resp = self.session.get(url, headers=headers)
            resp.raise_for_status()

            save_file_path = os.path.join(self.save_folder,f'{repo}.cfg')

            with open(save_file_path, "wb") as f:
                f.write(resp.content)
            
            return save_file_path

        except Exception as e:
            print(f"请求失败，状态码：{resp.status_code}，内容：{resp.text}")
            
            return None

    def _convert_cfg_to_dict(self, save_file_path):
        line_pattern = re.compile(
            r'-RESULT_FILTER\('
            r'([^,]+),'                              # 文件匹配部分，到逗号结束
            r'\s*TOOL_NUMBER\(([^)]+)\)\s+'         # TOOL_NUMBER(...)
            r'GUIDELINE\(([^)]+)\)'                  # GUIDELINE(...)
            r'(.+?)\)?$'                             # 后面紧跟提示信息，可能有括号结束，非贪婪匹配
        )

        guidline_pattern = re.compile(r'^([^:]*):[^:]*:([^:]*)$')
        
        # rules_dict = defaultdict(list)
        rules_dict = {}

        with open(save_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                m = line_pattern.match(line)

                if m:
                    raw_file = m.group(1)
                    guidline = m.group(3)
                    description = m.group(4).strip()

                    if raw_file == '*':
                        filename = '*'
                    else:
                        if raw_file.upper().startswith('ANY\\'):
                            filename = raw_file[4:]
                        elif raw_file.startswith('"FP.FilePath CONTAINS '):
                            filename = raw_file[23:-2]
                        else:
                            filename = raw_file


                    n = guidline_pattern.match(guidline)

                    if n:
                        code_rule, code_rule_chapter = n.groups()

                        if filename not in rules_dict:
                            rules_dict[filename] = {
                                'code_rules': [],
                                'code_rule_chapters': [],
                                'descriptions': []
                            }

                        if code_rule not in rules_dict[filename]['code_rules']:
                            rules_dict[filename]['code_rules'].append(code_rule)

                        if code_rule_chapter not in rules_dict[filename]['code_rule_chapters']:
                            rules_dict[filename]['code_rule_chapters'].append(code_rule_chapter)

                        if description not in rules_dict[filename]['descriptions']:
                            rules_dict[filename]['descriptions'].append(description)

        base, _ = os.path.splitext(save_file_path)
        rules_dict_file_path = base + ".pkl"

        with open(rules_dict_file_path, 'wb') as f:
            pickle.dump(rules_dict, f)

        return rules_dict

def read(): # For Debug, only for debug
    with open('/mnt/SHARE/cict_proj/99_Tools/RevBotV2/lib/gee-crx-24-zcu/GEE_CRX_24_ZCU_ZCUD_M_Multicore_APP.pkl', 'rb') as f:
        loaded_rules = pickle.load(f)

if __name__ == '__main__':
    load_dotenv(ENV_PATH)

    qp = QtoolsProcessor(owner = 'gee-crx-24-zcu')
    qp.processor()
