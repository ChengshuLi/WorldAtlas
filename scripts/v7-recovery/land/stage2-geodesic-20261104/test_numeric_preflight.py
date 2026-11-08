"""Run the unchanged coverage/population contract tests against the prototype."""
from unittest import mock

import numeric_preflight
from test_preflight import Preflight,RulePopulation


class _NumericMixin:
    def setUp(self):
        super().setUp()
        patcher=mock.patch('test_preflight.validate',new=numeric_preflight.validate)
        patcher.start();self.addCleanup(patcher.stop)


class NumericCoverage(_NumericMixin,Preflight):pass
class NumericPopulation(_NumericMixin,RulePopulation):pass
