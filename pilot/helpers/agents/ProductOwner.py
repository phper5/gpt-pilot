import json
from utils.style import color_green_bold
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from logger.logger import logger
from database.database import get_app, save_progress, save_app, get_progress_steps, get_project,save_project,get_created_project_apps_with_steps
from utils.utils import should_execute_step, generate_app_data, step_already_finished, clean_filename
from utils.files import setup_workspace
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, ask_user
from const.llm import END_RESPONSE
from utils.locale import get_translator
from const.messages import MAX_PROJECT_NAME_LENGTH
from const.common import EXAMPLE_PROJECT_DESCRIPTION
import sys
import uuid

PROJECT_DESCRIPTION_STEP = 'project_description'
USER_STORIES_STEP = 'user_stories'
USER_TASKS_STEP = 'user_tasks'
_ = get_translator()


class ProductOwner(Agent):
    def __init__(self, project):
        super().__init__('product_owner', project)

    def init_from_app(self):
        self.project.args['app_type'] = self.project.app.app_type
        self.project.args['name'] = self.project.app.name
        self.project.args['status'] = self.project.app.status
        self.project.args['continuing_project'] = True

    def create_project(self,spec_writer):
        print(json.dumps({
            "project_stage": "project"
        }), type='info', category='agent:product-owner')
        # 试图从app加载project,或者根据输入的project id加载project
        # 初始化self.project.project  和 self.project.args['project_id']
        if 'app_id' in self.project.args:
            self.project.app = get_app(self.project.args['app_id'])
        else:    
            self.project.app = None

        if self.project.app is not None:
            self.project.project = get_project(self.project.app.project_id)
            #用app进行初始化
            self.init_from_app()
            
        else:
            if 'project_id' in self.project.args:
                self.project.project = get_project(self.project.args['project_id'])
            else:
                self.project.project = None
        
        #没有app_id,project_id,则创建新的project
        if self.project.project is None:
            #创建新的project
            self.project.args['project_id'] = str(uuid.uuid4())
            print(color_green_bold('\n------------------ STARTING NEW PROJECT ----------------------'))
            print("If you wish to continue with this project in future run:")
            print(color_green_bold(f'python {sys.argv[0]} project_id={self.project.args["project_id"]}'))
            print(color_green_bold('--------------------------------------------------------------\n'))

            if 'project_name' not in self.project.args:
                while True:
                    question = 'What is the project name?'
                    print(question, type='ipc')
                    print('start an example project', type='button')
                    project_name = ask_user(self.project, question)
                    if len(project_name) <= MAX_PROJECT_NAME_LENGTH:
                        break
                    else:
                        print(f"Hold your horses cowboy! Please, give project NAME with max {MAX_PROJECT_NAME_LENGTH} characters.")

                if project_name.lower() == 'start an example project':
                    is_example_project = True
                    project_name = 'Example Project'

                self.project.args['project_name'] = clean_filename(project_name)
            question = '请输入项目的介绍?'
            project_description = ask_user(self.project, question)
            self.project.args['description'] = project_description
            self.project.args['app_type'] = ask_for_app_type()
            self.project.project = save_project(self.project)
        else:
            #用project进行初始化
            self.project.args['project_id'] = self.project.project.id
            self.project.args['description'] = self.project.project.description
            self.project.args['project_name'] = self.project.project.name
            self.project.args['app_type'] = self.project.project.app_type
            pass
        self.project.set_root_path(setup_workspace(self.project.args))




    def get_project_description(self, spec_writer):
        print(json.dumps({
            "project_stage": "requirement_description"
        }), type='info', category='agent:product-owner')

        # self.project.app = get_app(self.project.args['app_id'], error_if_not_found=False)
        # 已经在create_project处读取
       

        # If this app_id already did this step, just get all data from DB and don't ask user again
        if self.project.app is not None:
            step = get_progress_steps(self.project.args['app_id'], PROJECT_DESCRIPTION_STEP)
            if step and not should_execute_step(self.project.args['step'], PROJECT_DESCRIPTION_STEP):
                step_already_finished(self.project.args, step)
                self.project.set_root_path(setup_workspace(self.project.args))
                self.project.project_description = step['summary']
                self.project.project_description_messages = step['messages']
                self.project.main_prompt = step['prompt']
                return
        else:
            if 'app_id' not in self.project.args:
                app_list = get_created_project_apps_with_steps(self.project.args['project_id'])
                #列出已经有的，请选择，或者创建
                # if ipc_client_instance is not None:
                #     print({ 'db_data': get_created_apps_with_steps() }, type='info')
                # else:
                if app_list is not None and len(app_list) > 0 :
                    print('----------------------------------------------------------------------------------------')
                    print('app_id                                step                 dev_step  name')
                    print('----------------------------------------------------------------------------------------')
                    print('\n'.join(f"{app['id']}: {app['status']:20}      "
                                    f"{'' if len(app['development_steps']) == 0 else app['development_steps'][-1]['id']:3}"
                                    f"  {app['name']}" for app in app_list))
                    question = '请输入您要继续的app_id或者直接输入您的新需求名称'
                else:
                    question = '请输入您的需求名称'
                
                while True:
                    # question = 'What is the task name?'
                    print(question, type='ipc')
                    print('start an example project', type='button')
                    project_name = ask_user(self.project, question)
                    if len(project_name) <= MAX_PROJECT_NAME_LENGTH:
                        break
                    else:
                        print(f"Hold your horses cowboy! Please, give project NAME with max {MAX_PROJECT_NAME_LENGTH} characters.")
                #判断用户的输入project_name是否在apps的app_id中
                if app_list is not None and len(app_list) > 0 and project_name in app_list:

                    self.project.args['app_id'] = project_name
                    self.project.app = get_app(self.project.args['app_id'])
                    #todo 初始化 app
                    self.init_from_app()
                else:
                    self.project.args['name'] = clean_filename(project_name)
                self.project.args['app_id'] = str(uuid.uuid4())
                print(color_green_bold('\n------------------ STARTING NEW REQUIREMENT ----------------------'))
                print("If you wish to continue with this feature in future run:")
                print(color_green_bold(f'python {sys.argv[0]} app_id={self.project.args["app_id"]}'))
                print(color_green_bold('--------------------------------------------------------------\n'))

        # PROJECT DESCRIPTION
        self.project.current_step = PROJECT_DESCRIPTION_STEP
        is_example_project = False

        # if 'app_type' not in self.project.args:
        #     self.project.args['app_type'] = ask_for_app_type()
        # if 'name' not in self.project.args:
        #     while True:
        #         question = 'What is the task name?'
        #         print(question, type='ipc')
        #         print('start an example project', type='button')
        #         project_name = ask_user(self.project, question)
        #         if len(project_name) <= MAX_PROJECT_NAME_LENGTH:
        #             break
        #         else:
        #             print(f"Hold your horses cowboy! Please, give project NAME with max {MAX_PROJECT_NAME_LENGTH} characters.")

        #     if project_name.lower() == 'start an example task':
        #         is_example_project = True
        #         project_name = 'Example Task'

        #     self.project.args['name'] = clean_filename(project_name)

        self.project.app = save_app(self.project)
        self.init_from_app()
        #应该移动到create_project
        # self.project.set_root_path(setup_workspace(self.project.args))

        if is_example_project:
            print(EXAMPLE_PROJECT_DESCRIPTION)
            self.project.main_prompt = EXAMPLE_PROJECT_DESCRIPTION
        else:
            print(color_green_bold(
                "GPT Pilot currently works best for web app projects using Node, Express and MongoDB. "
                "You can use it with other technologies, but you may run into problems "
                "(eg. React might not work as expected).\n"
            ))
            self.project.main_prompt = ask_for_main_app_definition(self.project)

        print(json.dumps({'open_project': {
            #'uri': 'file:///' + self.project.root_path.replace('\\', '/'),
            'path': self.project.root_path,
            'name': self.project.args['name'],
        }}), type='info')

        high_level_messages = []
        high_level_summary = spec_writer.create_spec(self.project.main_prompt)

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "prompt": self.project.main_prompt,
            "messages": high_level_messages,
            "summary": high_level_summary,
            "app_data": generate_app_data(self.project.args)
        })

        self.project.project_description = high_level_summary
        self.project.project_description_messages = high_level_messages
        return
        # PROJECT DESCRIPTION END

    def get_user_stories(self):
        return ;
        if not self.project.args.get('advanced', False):
            return

        print(json.dumps({
            "project_stage": "user_stories"
        }), type='info')

        self.project.current_step = USER_STORIES_STEP
        self.convo_user_stories = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], USER_STORIES_STEP)
        if step and not should_execute_step(self.project.args['step'], USER_STORIES_STEP):
            step_already_finished(self.project.args, step)
            self.convo_user_stories.messages = step['messages']
            self.project.user_stories = step['user_stories']
            return

        # USER STORIES
        msg = "User Stories:\n"
        print(color_green_bold(msg))
        logger.info(msg)

        self.project.user_stories = self.convo_user_stories.continuous_conversation('user_stories/specs.prompt', {
            'name': self.project.args['name'],
            'prompt': self.project.project_description,
            'app_type': self.project.args['app_type'],
            'END_RESPONSE': END_RESPONSE
        })

        logger.info(f"Final user stories: {self.project.user_stories}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_stories": self.project.user_stories,
            "app_data": generate_app_data(self.project.args)
        })

        return
        # USER STORIES END

    def get_user_tasks(self):
        self.project.current_step = USER_TASKS_STEP
        self.convo_user_stories.high_level_step = self.project.current_step

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], USER_TASKS_STEP)
        if step and not should_execute_step(self.project.args['step'], USER_TASKS_STEP):
            step_already_finished(self.project.args, step)
            return step['user_tasks']

        # USER TASKS
        msg = "User Tasks:\n"
        print(color_green_bold(msg))
        logger.info(msg)

        self.project.user_tasks = self.convo_user_stories.continuous_conversation('user_stories/user_tasks.prompt',
                                                                                  {'END_RESPONSE': END_RESPONSE})

        logger.info(f"Final user tasks: {self.project.user_tasks}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_tasks": self.project.user_tasks,
            "app_data": generate_app_data(self.project.args)
        })

        return self.project.user_tasks
        # USER TASKS END
