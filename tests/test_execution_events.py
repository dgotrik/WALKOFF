import unittest

import walkoff.appgateway
import walkoff.case.database as case_database
import walkoff.case.subscription as case_subscription
import walkoff.config.config
import walkoff.config.paths
from tests import config
from tests.util import execution_db_help
from tests.util.mock_objects import *
from walkoff.multiprocessedexecutor import multiprocessedexecutor


class TestExecutionEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        execution_db_help.setup_dbs()
        walkoff.appgateway.cache_apps(config.test_apps_path)
        walkoff.config.config.load_app_apis(apps_path=config.test_apps_path)
        multiprocessedexecutor.MultiprocessedExecutor.initialize_threading = mock_initialize_threading
        multiprocessedexecutor.MultiprocessedExecutor.wait_and_reset = mock_wait_and_reset
        multiprocessedexecutor.MultiprocessedExecutor.shutdown_pool = mock_shutdown_pool
        multiprocessedexecutor.multiprocessedexecutor.initialize_threading()

    def setUp(self):
        self.executor = multiprocessedexecutor.multiprocessedexecutor
        case_database.initialize()

    def tearDown(self):
        execution_db_help.cleanup_device_db()

        case_database.case_db.session.query(case_database.Event).delete()
        case_database.case_db.session.query(case_database.Case).delete()
        case_database.case_db.session.commit()
        case_database.case_db.tear_down()

    @classmethod
    def tearDownClass(cls):
        walkoff.appgateway.clear_cache()
        multiprocessedexecutor.multiprocessedexecutor.shutdown_pool()
        execution_db_help.tear_down_device_db()

    def test_workflow_execution_events(self):
        workflow = execution_db_help.load_workflow('multiactionWorkflowTest', 'multiactionWorkflow')
        subs = {'case1': {str(workflow.id): [WalkoffEvent.AppInstanceCreated.signal_name,
                                             WalkoffEvent.WorkflowShutdown.signal_name]}}
        case_subscription.set_subscriptions(subs)
        self.executor.execute_workflow(workflow.id)

        self.executor.wait_and_reset(1)
        execution_events = case_database.case_db.session.query(case_database.Case) \
            .filter(case_database.Case.name == 'case1').first().events.all()

        self.assertEqual(len(execution_events), 2,
                         'Incorrect length of event history. '
                         'Expected {0}, got {1}'.format(2, len(execution_events)))

    def test_action_execution_events(self):
        workflow = execution_db_help.load_workflow('basicWorkflowTest', 'helloWorldWorkflow')
        action_ids = [str(action.id) for action in workflow.actions]
        action_events = [WalkoffEvent.ActionExecutionSuccess.signal_name, WalkoffEvent.ActionStarted.signal_name]
        subs = {'case1': {action_id: action_events for action_id in action_ids}}
        case_subscription.set_subscriptions(subs)

        self.executor.execute_workflow(workflow.id)

        self.executor.wait_and_reset(1)

        execution_events = case_database.case_db.session.query(case_database.Case) \
            .filter(case_database.Case.name == 'case1').first().events.all()
        self.assertEqual(len(execution_events), 2,
                         'Incorrect length of event history. '
                         'Expected {0}, got {1}'.format(2, len(execution_events)))

    # TODO: Rewrite this test. This workflow has no branches because there is only one action.
    # def test_condition_transform_execution_events(self):
    #     # self.c.load_playbook(resource=config.test_workflows_path + 'basicWorkflowTest.playbook')
    #     workflow = self.c.get_workflow('basicWorkflowTest', 'helloWorldWorkflow')
    #     action_id = None
    #     for action in workflow.actions:
    #         if action.name == 'repeatBackToMe':
    #             action_id = action.id
    #
    #     subs = {action_id: [WalkoffEvent.ActionExecutionSuccess.signal_name, WalkoffEvent.ActionStarted.signal_name]}
    #     branch = workflow.branches[0]
    #     subs[branch.id] = [WalkoffEvent.BranchTaken.signal_name, WalkoffEvent.BranchNotTaken.signal_name]
    #     condition = next(condition for condition in branch.conditions if condition.action_name == 'regMatch')
    #     subs[condition.id] = [WalkoffEvent.ConditionSuccess.signal_name, WalkoffEvent.ConditionError.signal_name]
    #     transform = next(transform for transform in condition.transforms if transform.action_name == 'length')
    #     subs[transform.id] = [WalkoffEvent.TransformSuccess.signal_name, WalkoffEvent.TransformError.signal_name]
    #
    #     case_subscription.set_subscriptions({'case1': subs})
    #
    #     self.c.execute_workflow('basicWorkflowTest', 'helloWorldWorkflow')
    #
    #     self.c.wait_and_reset(1)
    #
    #     events = case_database.case_db.session.query(case_database.Case) \
    #         .filter(case_database.Case.name == 'case1').first().events.all()
    #     self.assertEqual(len(events), 5,
    #                      'Incorrect length of event history. '
    #                      'Expected {0}, got {1}'.format(5, len(events)))
