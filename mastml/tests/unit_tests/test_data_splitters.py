from mastml.models import SklearnModel
from mastml.data_splitters import LeaveOutTwinCV, NoSplit, SklearnDataSplitter, LeaveCloseCompositionsOut, LeaveOutPercent, \
    Bootstrap, JustEachGroup
import unittest
import pandas as pd
import numpy as np
import os
import shutil
import sys

sys.path.insert(0, os.path.abspath('../../../'))


class TestSplitters(unittest.TestCase):

    def test_nosplit(self):
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(10, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(10,)))
        model = SklearnModel(model='LinearRegression')
        splitter = NoSplit()
        splitter.evaluate(X=X, y=y, models=[model], savepath=os.getcwd())
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return

    def test_sklearnsplitter(self):
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(10, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(10,)))
        model = SklearnModel(model='LinearRegression')
        splitter = SklearnDataSplitter(splitter='KFold', shuffle=True, n_splits=5)
        splitter.evaluate(X=X, y=y, models=[model], savepath=os.getcwd())
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return

    def test_close_comps(self):
        # Make entries at a 10% spacing
        composition_df = pd.DataFrame({'composition': ['Al{}Cu{}'.format(i, 10-i) for i in range(11)]})
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(11, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(11,)))

        # Generate test splits with a 5% distance cutoff
        splitter = LeaveCloseCompositionsOut(composition_df=composition_df, dist_threshold=0.5)

        model = SklearnModel(model='LinearRegression')
        splitter.evaluate(X=X, y=y, models=[model])
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return

    def test_leaveoutpercent(self):
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(25, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(25,)))
        splitter = LeaveOutPercent(percent_leave_out=0.20, n_repeats=5)
        model = SklearnModel(model='LinearRegression')
        splitter.evaluate(X=X, y=y, models=[model], groups=None)
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return

    def test_bootstrap(self):
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(25, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(25,)))
        splitter = Bootstrap(n=25, n_bootstraps=3, train_size=0.5)
        model = SklearnModel(model='LinearRegression')
        splitter.evaluate(X=X, y=y, models=[model], groups=None)
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return

    def test_justeachgroup(self):
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(5, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(5,)))
        groups = pd.DataFrame.from_dict({'groups': [0, 1, 1, 0, 1]})
        X = pd.concat([X, groups], axis=1)
        splitter = JustEachGroup()
        model = SklearnModel(model='LinearRegression')
        splitter.evaluate(X=X, y=y, models=[model], groups=X['groups'])
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return

    def test_leaveoutwincv(self):
        # implemented = False
        # self.assertTrue(implemented)

        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(25, 10)))
        y = pd.Series(np.random.uniform(low=0.0, high=100, size=(25,)))
        splitter = LeaveOutTwinCV(1)
        model = SklearnModel(model='LinearRegression')
        splitter.evaluate(X=X, y=y, models=[model], groups=None)
        for d in splitter.splitdirs:
            self.assertTrue(os.path.exists(d))
            shutil.rmtree(d)
        return


if __name__ == '__main__':
    unittest.main()
