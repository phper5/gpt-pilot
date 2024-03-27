from database.database import database_exists, create_database, tables_exist, create_tables, get_created_apps_with_steps
from logger.logger import logger
from utils.arguments import get_arguments
from utils.custom_print import get_custom_print
import builtins
from helpers.Project import Project
from utils.telemetry import telemetry
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, ask_user
from const.messages import MAX_PROJECT_NAME_LENGTH
from utils.style import color_green_bold, color_red, style_config
import uuid
import sys
import os
from utils.settings import settings, loader, get_version

class Application:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Application, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
       self.arguments = None
       pass

    def init(self):
        if not database_exists():
            create_database()

        # Check if the tables exist, if not, create them
        if not tables_exist():
            create_tables()
        
    def get_project(self):
        if self.arguments is None:
            self.arguments = get_arguments()

        if '--api-key' in self.arguments:
            os.environ["OPENAI_API_KEY"] = self.arguments['--api-key']
        if '--api-endpoint' in self.arguments:
            os.environ["OPENAI_ENDPOINT"] = self.arguments['--api-endpoint']
        
        if '--version' in self.arguments:
            print(get_version())
            run_exit_fn = False

        elif '--ux-test' in self.arguments:
            from test.ux_tests import run_test
            run_test(self.arguments['--ux-test'], self.arguments)
            run_exit_fn = False

        logger.info('Starting with args: %s', self.arguments)
        builtins.print, ipc_client_instance = get_custom_print(self.arguments)
        project = Project(self.arguments, ipc_client_instance=ipc_client_instance)
        if project.check_ipc():
            telemetry.set("is_extension", True)
        if 'app_id' not in self.arguments:
            apps = get_created_apps_with_steps()
            if ipc_client_instance is not None:
                    print({ 'db_data': apps }, type='info')
            else:
                    print('----------------------------------------------------------------------------------------')
                    print('app_id                                step                 dev_step  name')
                    print('----------------------------------------------------------------------------------------')
                    print('\n'.join(f"{app['id']}: {app['status']:20}      "
                                    f"{'' if len(app['development_steps']) == 0 else app['development_steps'][-1]['id']:3}"
                                    f"  {app['name']}" for app in apps))
                    while True:
                        question = 'Please the app by app_id or enter your project name?'
                        print(question, type='ipc')
                        print('start an example project', type='button')
                        project_name = ask_user(project, question)
                        if len(project_name) <= MAX_PROJECT_NAME_LENGTH:
                            break
                        else:
                            print(f"Hold your horses cowboy! Please, give project NAME with max {MAX_PROJECT_NAME_LENGTH} characters.")
                    #判断用户的输入是否在apps的id中
                    if project_name in apps:
                        self.arguments['app_id'] = project_name
                    else:
                        self.arguments['name'] = project_name
                        self.arguments['app_id'] = str(uuid.uuid4())
                        print(color_green_bold('\n------------------ STARTING NEW PROJECT ----------------------'))
                        print("If you wish to continue with this project in future run:")
                        print(color_green_bold(f'python {sys.argv[0]} app_id={self.arguments["app_id"]}'))
                        print(color_green_bold('--------------------------------------------------------------\n'))
                        project.args['app_id'] = self.arguments['app_id']
                        project.args['name'] = project_name
                    
        return project
    
    #todo 以下方法似乎没有时间的机会
    def set_arguments(self, arguments):
        self.arguments = arguments

    def set_argument(self, key, value):
        if self.arguments is None:
            self.arguments = {}
        self.arguments[key] = value
        