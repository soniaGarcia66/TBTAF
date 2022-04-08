from __future__ import absolute_import
import cx_Oracle
import os
from common.suite import TBTestSuite
from common.metadata import TBMetadata
from common.result import TBTAFResult
from common.printable_test import TBTAFPrintableTest
from publisher.TBTAFPublisher import TBTAFPublisher
from common.enums.metadata_type import TBTAFMetadataType


class TBTAFDataBridge(object):

    connection = cx_Oracle.connect(os.environ['ODB_USER'], os.environ['ODB_PASS'], os.environ['ODB_TNS'])
    
    def __init__(self):
        #Constructor
        pass

    def storeResult(self, tBTestSuiteInstance):
        '''
        Store a test execution report into the database
        based on the execution result of a given test suite
        '''
        cursor = TBTAFDataBridge.connection.cursor()
        new_id = cursor.var(cx_Oracle.NUMBER)
        #Get summary result from the test suite instance
        summaryTestSuite = tBTestSuiteInstance.getSuiteResult()
        #Calculate total number of test cases
        totalTests = len(tBTestSuiteInstance.suiteTestCases)
        #Calculate success rate of test summary results 
        successRate = (float(summaryTestSuite.passTests) / float(totalTests))*100

        testSuiteSqlParams = {
            "suite_type" : str(tBTestSuiteInstance.getTestSuiteType()),
            "suite_id" : str(tBTestSuiteInstance.getSuiteID()),
            "total_test" : int(totalTests),
            "passed_test" : int(summaryTestSuite.passTests),
            "failed_test" : int(summaryTestSuite.failedTests),
            "inconclusive_test" : int(summaryTestSuite.inconclusiveTests),
            "success_rate" : int(successRate),
            "start_time" : summaryTestSuite.getStartTimestamp(),
            "end_time" : summaryTestSuite.getEndTimestamp(),
            "time_elapse" : str(summaryTestSuite.getEndTimestamp() - summaryTestSuite.getStartTimestamp()),
            "new_id" : new_id
         }
        print("test suit Summary inserted")
        cursor.execute(TBTAFDataBridge.testSuiteInsertSql, testSuiteSqlParams)
        #Get auto-generated id
        newest_id = new_id.getvalue()
        testCasesList = tBTestSuiteInstance.getTestCases()
        
        #Iterate over test cases and retrieve test metadata
        for testCase in testCasesList:
            testMetaData = testCase.getTestMetadata()
            testTags = testMetaData.getTags()
            tagsConcatenated = ""
            for tag in testTags:
                tagsConcatenated = tagsConcatenated + tag + ","
            #Remove last character from tags
            tagsConcatenated = tagsConcatenated[:-1]
            testResult = testCase.getResult()

            testSqlParams = {
                "test_id" : str(testMetaData.getAssetID()), 
                "description" : testMetaData.getAssetDescription(), 
                "tags" : tagsConcatenated, 
                "priority" : str(testMetaData.getPriority()), 
                "source" : testResult.getResultSource(), 
                "start_time" : testResult.getStartTimestamp(), 
                "end_time" : testResult.getEndTimestamp(), 
                "time_elapse" : str(testResult.getEndTimestamp() - testResult.getStartTimestamp()), 
                "veredict" : str(testResult.getVerdict()), 
                "suite_id" : newest_id[0]
            }
            cursor.execute(TBTAFDataBridge.testInsertSql, testSqlParams)
        TBTAFDataBridge.connection.commit()
        print("All test data inserted")
        cursor.close()
        return newest_id[0]

    def getTestResultBySuiteId(self, suiteId, path, format):
        '''
        Get a test execution report into the database
        based on the execution result of a given test suite
        '''
        cursor = TBTAFDataBridge.connection.cursor()
        cursor.execute(TBTAFDataBridge.testSuiteSelectSql, id=int(suiteId))
        columns = [col[0] for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))
        testSiutes = cursor.fetchall()
        for row in testSiutes:
            testSuite = TBTestSuite(row['SUITE_TYPE'],row['SUITE_ID'])
            cursor.execute(TBTAFDataBridge.testSelectSql, suite_id=int(suiteId))
            columns = [col[0] for col in cursor.description]
            cursor.rowfactory = lambda *args: dict(zip(columns, args))
            tests = cursor.fetchall()
            for test in tests:
                testMetadata = TBMetadata(TBTAFMetadataType.PRINTABLE_CODE)
                testMetadata.setAssetDescription(test['DESCRIPTION'])
                testMetadata.setAssetID(int(test['TEST_ID']))
                testMetadata.setPriority(int(test['PRIORITY']))
                testMetadata.setTags(test['TAGS'].split(','))
                testResult = TBTAFResult(resultSource=test['SOURCE'], testVerdict=test['VEREDICT'])
                testResult.setStartTimestamp(test['START_TIME'])
                testResult.setEndTimestamp(test['END_TIME'])
                printableTest = TBTAFPrintableTest(metadata=testMetadata, result=testResult)
                testSuite.addTestCase(printableTest)
            TBTAFPublisher().PublishResultReport(testSuite,  path, format)
        cursor.close()

    testSuiteInsertSql = """INSERT INTO test_suite (
        suite_type, 
        suite_id, 
        total_test, 
        passed_test, 
        failed_test, 
        inconclusive_test, 
        success_rate, 
        start_time, 
        end_time, 
        time_elapse) 
        VALUES(            
        :suite_type, 
        :suite_id, 
        :total_test, 
        :passed_test, 
        :failed_test, 
        :inconclusive_test, 
        :success_rate, 
        :start_time, 
        :end_time, 
        :time_elapse)
        returning id into :new_id"""

    testInsertSql = """INSERT INTO test (
        test_id,
        description,
        tags,
        priority,
        source,
        start_time,
        end_time,
        time_elapse,
        veredict,
        suite_id)
     VALUES(            
        :test_id,
        :description,
        :tags,
        :priority,
        :source,
        :start_time,
        :end_time,
        :time_elapse,
        :veredict,
        :suite_id)"""

    testSuiteSelectSql = """SELECT
        suite_type, 
        suite_id
        FROM test_suite
        WHERE id = :id"""


    testSelectSql = """SELECT
        test_id,
        description,
        tags,
        priority,
        source,
        start_time,
        end_time,
        time_elapse,
        veredict,
        suite_id
        FROM test
        WHERE suite_id = :suite_id"""
