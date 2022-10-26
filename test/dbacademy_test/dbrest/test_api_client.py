# Databricks notebook source
# MAGIC %pip install \
# MAGIC git+https://github.com/databricks-academy/dbacademy-gems \
# MAGIC --quiet --disable-pip-version-check

# COMMAND ----------

import unittest

from dbacademy.common import print_warning
from dbacademy.rest.common import ApiClient
from dbacademy.dougrest import databricks, DatabricksApiException


class TestApiClient(unittest.TestCase):
    """
    Test client error handling, retry, and backoff features.
    """

    def testApiSimple(self):
        results = databricks.api("GET", "/2.0/workspace/list", path="/")
        self.assertIsNotNone(results)

    def testExpected404(self):
        results = databricks.api("GET", "/2.0/workspace/list", path="/does-not-exist", _expected=404)
        self.assertIsNone(results)

    def testSelfCallable(self):
        self.assertEqual(databricks, databricks())

    def testWithHostname(self):
        # We intentionally pass in a full URL as part of testing for legacy compatibility.
        url = databricks.url + "2.0/workspace/list?path=/"
        results = databricks.api("GET", url)

    def testWithHttps(self):
        url = "https://unknown.domain.com/api/2.0/workspace/list?path=/"
        try:
            databricks.api("GET", url)
            self.fail("Expected ValueError due to 'https:' in URL.")
        except ValueError:
            pass

    def testExecuteGetJsonExpected404(self):
        url = "2.0/workspace/list?path=/does-not-exist"
        results = databricks.api("GET", url, _expected=404)
        self.assertIsNone(results)

    def testNotFound(self):
        try:
            databricks.api("GET", "does-not-exist")
            self.fail("404 DatabricksApiException expected")
        except DatabricksApiException as e:
            self.assertEqual(e.http_code, 404)

    def testUnauthorized(self):
        try:
            client = ApiClient(databricks.url, token="INVALID")
            client.api("GET", "2.0/workspace/list")
            self.fail("403 DatabricksApiException expected")
        except DatabricksApiException as e:
            self.assertIn(e.http_code, (401, 403))

    def testThrottle(self):
        print()
        print_warning("WARNING", "Ignore the next throttle warning.  It is intentionally being testing.")
        client = ApiClient(databricks.url,
                           authorization_header=databricks.session.headers["Authorization"],
                           throttle_seconds=2
                           )
        import time
        t1 = time.time()
        client.api("GET", "2.0/clusters/list-node-types")
        t2 = time.time()
        client.api("GET", "2.0/clusters/list-node-types")
        t3 = time.time()
        self.assertLess(t2-t1, 1)
        self.assertGreater(t3-t2, 1)


# COMMAND ----------

def main():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApiClient))
    runner = unittest.TextTestRunner()
    runner.run(suite)


# COMMAND ----------

if __name__ == '__main__':
    main()
