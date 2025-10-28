from flask import request, Flask
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from  main import main

class PRHookApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.add_routes()

    def add_routes(self):
        self.app.add_url_rule('/revbot-webhook/', view_func=self.pr_webhook, methods=['POST'])

    def pr_webhook(self):
       return main(request=request)

pr_hook_app = PRHookApp()
app = pr_hook_app.app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
