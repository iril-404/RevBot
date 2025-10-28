import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re
import logging

from dotenv import load_dotenv

from main import main
from src.modules import setup_logging
from configs.config import PROJECT_MAPPING, ENV_PATH

def trigger(pr_url):
    logger = logging.getLogger(__name__)

    match = re.search(r"github-ix\.int\.automotive-wan\.com/([^/]+)/([^/]+)/pull/\d+", pr_url)

    try:
        org = match.group(1)
        repo = match.group(2)

    except AttributeError:
        org = None
        repo = None
        logger.error(f"Failed to parse org and repo from PR URL: {pr_url}")

    else:
        if org in PROJECT_MAPPING:
            project = PROJECT_MAPPING[org]["Project"]
            setup_logging(project=project)
            logger = logging.getLogger(__name__)
            logger.info('============================== Start Handler ==============================')
            logger.info(f"Parsed org: '{org}', repo: '{repo}' from URL.")
            # 模拟 GitHub 请求
            class MockRequest:
                def __init__(self):
                    self.headers = {
                        'X-GitHub-Event': 'pull_request'
                    }
                    self.json = {
                        'action': 'opened',
                        'repository': {
                            'owner': {
                                'login': org
                            },
                            'name': repo,
                            'url': f'https://api.github.com/repos/{org}/{repo}'
                        },
                        'pull_request': {
                            'html_url': pr_url
                        }
                    }
            request = MockRequest()
            result = main(request)
            print(result)

            logger.info('============================== End Handler ==============================')
            return 'OK', 200
        
        else:
            logger.warning(f"Org '{org}' not found in project_map. PR URL: {pr_url}")

if __name__ == '__main__':
    load_dotenv(ENV_PATH)
    trigger(pr_url='https://github-ix.int.automotive-wan.com/gee-crx-24-zcu/GEE_CRX_24_ZCU_ZCUD_M_Multicore_APP/pull/7833')
    