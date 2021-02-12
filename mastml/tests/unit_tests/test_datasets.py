import unittest
import numpy as np
import pandas as pd
import os
import sys
import shutil
sys.path.insert(0, os.path.abspath('../../../'))

from mastml.datasets import SklearnDatasets, LocalDatasets, FoundryDatasets, DataCleaning

class TestDatasets(unittest.TestCase):

    def test_sklearn(self):
        sklearndata = SklearnDatasets(return_X_y=True, as_frame=True)
        bostonX, bostony = sklearndata.load_boston()
        irisX, irisy = sklearndata.load_iris()
        digitsX, digitsy = sklearndata.load_digits()
        diabetesX, diabetesy = sklearndata.load_diabetes()
        breast_cancerX, breast_cancery = sklearndata.load_breast_cancer()
        wineX, winey = sklearndata.load_wine()
        linnerudX, linnerudy = sklearndata.load_linnerud()
        self.assertEqual(bostonX.shape, (506,13))
        self.assertEqual(irisX.shape, (150,4))
        self.assertEqual(digitsX.shape, (1797,64))
        self.assertEqual(diabetesX.shape, (442,10))
        self.assertEqual(breast_cancerX.shape, (569,30))
        self.assertEqual(wineX.shape, (178,13))
        self.assertEqual(linnerudX.shape, (20,3))
        return

    '''
    def test_figshare(self):
        FigshareDatasets().download_data(article_id='7418492', savepath=os.getcwd())
        self.assertTrue(os.path.exists('figshare_7418492'))
        return
    '''

    def test_local(self):
        target = 'E_regression.1'
        extra_columns = ['E_regression', 'Material compositions 1', 'Material compositions 2', 'Hop activation barrier']
        d = LocalDatasets(file_path='figshare_7418492/All_Model_Data.xlsx',
                          target=target,
                          extra_columns=extra_columns,
                          as_frame=True)
        X, y = d.load_data()
        self.assertEqual(X.shape, (408,287))
        self.assertEqual(y.shape, (408,))
        shutil.rmtree('figshare_7418492')
        return

    def test_foundry(self):
        foundrydata = FoundryDatasets(no_local_server=False, anonymous=True, test=True)
        foundrydata.download_data(name='pub_57_wu_highthroughput', download=False)
        return

class TestDataCleaning(unittest.TestCase):

    def test_datacleaning(self):
        X = pd.DataFrame(np.random.uniform(low=0.0, high=100, size=(50, 10)))
        y_input = pd.Series(np.random.uniform(low=0.0, high=100, size=(50,)))
        y_input.name = 'target'
        X_input = X.mask(np.random.random(X.shape) < 0.1)
        DataCleaning().remove(X=X_input, y=y_input, axis=1)
        DataCleaning().imputation(X=X_input, y=y_input, strategy='mean')
        DataCleaning().ppca(X=X_input, y=y_input)
        cleaner = DataCleaning()
        cleaner.evaluate(X=X_input, y=y_input, method='remove', axis=1, savepath=os.getcwd())
        self.assertTrue(os.path.exists(cleaner.splitdir))
        shutil.rmtree(cleaner.splitdir)
        return

if __name__=='__main__':
    unittest.main()