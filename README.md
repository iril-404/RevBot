# RevBot

![image](https://github-ix.int.automotive-wan.com/uig21905/RevBot/assets/27894/5a1861d8-2477-4e7a-8aa2-21017e7180a9)
https://shx00136vmx.shx.cn.int.automotive-wan.com:8080/job/release_AI_assist/

## Instaliaton

1. Create and Activate conda environment
   ```bash
   conda create -n RB python=3.11 -y
   conda activate RB
   ```

2. Install dependancy
   ```bash
   cd <Path/To/RevBot/Root/Folder>
   pip install -r requirements.txt 
   ```

3. Setup RevBot as Python Package
   ```bash
   pip install -e .
   ```

4. Setup RevBot Config in ```/configs/config.py```
   * Required:
   ```bash
   Change ROOT_PATH
   ```

   * Opiniontal:
   ```bash
   Change JIRA_PATH/GITHUB_URL
   Add PROJECT_MAPPING
   ```

   * Forbidden
   ```bash
   Do Not Change LOG_PATH
   ```

## Useage
1. Manual Triger for RevBot
   * Setup env
   ```bash
   cd <Path/To/RevBot/Root/Folder>/tools/manual_trigger.py
   setup env
   ```

   * Activate environment and run .py
   ```bash
   conda activate RB
   python manual_trigger.py
   ```

## Test