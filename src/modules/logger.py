import os
import datetime

import logging.config
from configs.config import LOG_PATH, PROJECT_MAPPING

def setup_watchdog(success, project, jira_link, pr_url):
    if project not in PROJECT_MAPPING:
        return
    folder_project = PROJECT_MAPPING.get(project, {}).get("Project", "")
    log_file = os.path.join(LOG_PATH, folder_project, 'log/watch_dog.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if success:
        log_line = f"{now_str} - SUCCESS - {jira_link} - {pr_url}\n"
    else:
        log_line = f"{now_str} - ERROR - {jira_link} - {pr_url}\n"

    with open(log_file, "a") as f:
        f.write(log_line)

def setup_logging(project):
    """
    logger setup
    """
    
    log_dir = os.path.join(LOG_PATH, project, 'log')
    os.makedirs(log_dir, exist_ok=True)

    # Log File Name
    log_filename = datetime.datetime.now().strftime('%y%m%d_RevBot_Log.log')
    log_filepath = os.path.join(log_dir, log_filename)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.FileHandler',
                'filename': log_filepath,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            '': { 
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False
            }
        }
    })
