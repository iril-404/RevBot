import os

# HTTPS Link
JIRA_URL = "https://ix.jira.automotive.cloud/"
GITHUB_URL = "https://github-ix.int.automotive-wan.com"

# Project Path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ===================== FORBIDDEN CHANGE =====================
CONFIG_PATH =  os.path.join(ROOT_PATH, 'configs')
ENV_PATH = os.path.join(CONFIG_PATH, '.env')
LOG_PATH = os.path.join(ROOT_PATH, 'log')
LIB_PATH = os.path.join(ROOT_PATH, 'lib')
# ===================== FORBIDDEN CHANGE =====================


# Project Map
PROJECT_MAPPING = {
    "uig21905" : {
        "Project" : "RevBot",
        "Repo" : ["RevBot"]
    },
    
    "chy-e0x-25-zcu" : {
        "Project" : "CHERY_ZCU",
        "Repo" : ["CDD_Extension", "CHY_E0X_25_ZCU_P_APP", "CHY_E0X_25_ZCU_D_APP"]
    },

    "gee-crx-24-zcu" : {
        "Project" : "GEELY_ZCU",
        "Repo" : ["GEE_CRX_24_ZCU_ZCUD_M_Multicore_APP", 
                  "GEE_CRX_24_ZCU_ZCUP_APP", 
                  "GEE_CRX_24_ZCU_ZCUD_S_APP", 
                  "CAR_SWP_PKG", 
                  "ZCUL_GEE_CRX_25_ZCUD_M_Multicore_APP", 
                  "ZCUL_GEE_CRX_25_ZCUP_APP", 
                  "ZCUL_CAR_SWP_PKG"
                ],
        "Qtools_path" : ['tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg',
                         'tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg',
                         'tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg',
                         'tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg',
                         'tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg',
                         'tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg',
                         'tools/ci_scripts/cmb_swp_config/tools/qtools/qtools_result_filters.cfg'
                        ]
    }
}


