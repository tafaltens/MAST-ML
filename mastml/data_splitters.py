"""
The data_splitters module contains a collection of classes for generating (train_indices, test_indices) pairs from
a dataframe or a numpy array.

For more information and a list of scikit-learn splitter classes, see:
 http://scikit-learn.org/stable/modules/classes.html#module-sklearn.model_selection
"""

import numpy as np
import os
import pandas as pd
from datetime import datetime
import copy
import sklearn
import inspect
from pprint import pprint
import joblib
from math import ceil
import warnings

try:
    from matminer.featurizers.composition import ElementFraction
    from pymatgen import Composition
except:
    # pass if fails for autodoc build
    pass

import sklearn.model_selection as ms
from sklearn.utils import check_random_state
from sklearn.neighbors import NearestNeighbors

from mastml.plots import Histogram, Scatter
from mastml.feature_selectors import NoSelect


class BaseSplitter(ms.BaseCrossValidator):
    """
    Class functioning as a base splitter with methods for organizing output and evaluating any mastml data splitter

    Args:
        splitter (mastml.data_splitters object): a mastml.data_splitters object, e.g. mastml.data_splitters.SklearnDataSplitter
        kwargs : key word arguments for the sklearn.model_selection object, e.g. n_splits=5 for KFold()

    Methods:
        split_asframe: method to perform split into train indices and test indices, but return as dataframes

            Args:
                X: (pd.DataFrame), dataframe of X features
                y: (pd.Series), series of y target data
                groups: (pd.Series), series of group designations

            Returns:
                X_splits: (list), list of dataframes for X splits
                y_splits: (list), list of dataframes for y splits

        evaluate: main method to evaluate a sequence of models, selectors, and hyperparameter optimizers, build directories
            and perform analysis and output plots.

            Args:
                X: (pd.DataFrame), dataframe of X features
                y: (pd.Series), series of y target data
                models: (list), list containing masmtl.models instances
                groups: (pd.Series), series of group designations
                hyperopt: (list), list containing mastml.hyperopt instances
                selectors: (list), list containing mastml.feature_selectors instances
                savepath: (str), string containing main savepath to construct splits for saving output

            Returns:
                None

        _evaluate_split: method to evaluate a single data split, i.e. fit model, predict test data, and perform some
            plots and analysis.

            Args:
                X_train: (pd.DataFrame), dataframe of X training features
                X_test: (pd.DataFrame), dataframe of X test features
                y_train: (pd.Series), series of y training features
                y_test: (pd.Series), series of y test features
                model: (mastml.models instance), an estimator for fitting data
                splitpath: (str), string denoting the split path in the save directory

            Returns:
                None

        _save_split_data: method to save the X and y split data to excel files

            Args:
                df: (pd.DataFrame), dataframe of X or y data to save to file
                filename: (str), string denoting the filename, e.g. 'Xtest'
                savepath: (str), string denoting the save path of the file
                columns: (list), list of dataframe column names, e.g. X feature names

            Returns:
                None

        _collect_data: method to collect all Xtrain/Xtest/ytrain/ytest data into single series over many splits (directories)

            Args:
                filename: (str), string denoting the filename, e.g. 'Xtest'
                savepath: (str), string denoting the save path of the file

            Returns:
                data: (list), list containing flattened array of all data of a given type over many splits, e.g. all ypred data

        help: method to output key information on class use, e.g. methods and parameters

            Args:
                None

            Returns:
                None, but outputs help to screen
    """

    def __init__(self):
        super(BaseSplitter, self).__init__()
        self.splitter = self.__class__.__name__

    def split_asframe(self, X, y, groups=None):
        split = self.split(X, y, groups)
        X_splits = list()
        y_splits = list()
        for train, test in split:
            X_splits.append((X.iloc[train], X.iloc[test]))
            y_splits.append((y.iloc[train], y.iloc[test]))
        return X_splits, y_splits

    def evaluate(self, X, y, models, groups=None, hyperopt=None, selectors=None, savepath=None):
        # Have option to evaluate hyperparams of model in each split
        # Have ability to do nesting here?
        # How to handle which plots to make?
        # Carry data label name from metadata?

        X_splits, y_splits = self.split_asframe(X=X, y=y, groups=groups)

        if type(models) == list:
            pass
        else:
            models = list(models)

        if selectors is None:
            selectors = [NoSelect()]
        else:
            if type(selectors) == list:
                pass
            else:
                selectors = list(selectors)

        if not savepath:
            savepath = os.getcwd()

        self.splitdirs = list()
        for model in models:

            for selector in selectors:
                splitdir = self._setup_savedir(model=model, selector=selector, savepath=savepath)
                self.splitdirs.append(splitdir)

                # Here loop over hyperopt methods if provided, include in save dir name above
                #
                #

                split_count = 0
                for Xs, ys in zip(X_splits, y_splits):
                    model_orig = copy.deepcopy(model)

                    # Here do new split of Xtrain, ytrain to Xtrain2, ytrain2, Xval, yval for nested CV ???
                    #
                    #

                    X_train = Xs[0]
                    X_test = Xs[1]
                    y_train = pd.Series(np.array(ys[0]).ravel(), name='y_train')
                    y_test = pd.Series(np.array(ys[1]).ravel(), name='y_test')  # Make it so the y_test and y_pred have same indices so can be subtracted to get residuals
                    # make the individual split directory
                    splitpath = os.path.join(splitdir, 'split_' + str(split_count))
                    # make the feature selector directory for this split directory
                    os.mkdir(splitpath)

                    # run selector to get new Xtrain, Xtest
                    X_train = selector.evaluate(X=X_train, y=y_train)
                    X_test = selector.evaluate(X=X_test, y=y_test)

                    self._evaluate_split(X_train, X_test, y_train, y_test, model_orig, splitpath)
                    split_count += 1

                # At level of splitdir, do analysis over all splits (e.g. parity plot over all splits)
                y_test_all = self._collect_data(filename='y_test', savepath=splitdir)
                y_train_all = self._collect_data(filename='y_train', savepath=splitdir)
                y_pred_all = self._collect_data(filename='y_pred', savepath=splitdir)
                y_pred_train_all = self._collect_data(filename='y_pred_train', savepath=splitdir)

                Histogram.plot_residuals_histogram(y_true=y_test_all,
                                                   y_pred=y_pred_all,
                                                   savepath=splitdir,
                                                   file_name='residual_histogram_test',
                                                   show_figure=False)
                Histogram.plot_residuals_histogram(y_true=y_train_all,
                                                   y_pred=y_pred_train_all,
                                                   savepath=splitdir,
                                                   file_name='residual_histogram_train',
                                                   show_figure=False)
                Scatter.plot_predicted_vs_true(y_true=y_test_all,
                                               y_pred=y_pred_all,
                                               savepath=splitdir,
                                               file_name='parity_plot_allsplits_test',
                                               x_label='values',
                                               show_figure=False)
                Scatter.plot_predicted_vs_true(y_true=y_train_all,
                                               y_pred=y_pred_train_all,
                                               savepath=splitdir,
                                               file_name='parity_plot_allsplits_train',
                                               x_label='values',
                                               show_figure=False)
        return

    def _evaluate_split(self, X_train, X_test, y_train, y_test, model, splitpath):
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_pred_train = model.predict(X_train)

        Histogram.plot_residuals_histogram(y_true=y_test,
                                           y_pred=y_pred,
                                           savepath=splitpath,
                                           file_name='residual_histogram_test',
                                           show_figure=False)
        Histogram.plot_residuals_histogram(y_true=y_train,
                                           y_pred=y_pred_train,
                                           savepath=splitpath,
                                           file_name='residual_histogram_train',
                                           show_figure=False)
        Scatter.plot_predicted_vs_true(y_true=y_test,
                                       y_pred=y_pred,
                                       savepath=splitpath,
                                       file_name='parity_plot_test',
                                       x_label='values',
                                       show_figure=False)
        Scatter.plot_predicted_vs_true(y_true=y_train,
                                       y_pred=y_pred_train,
                                       savepath=splitpath,
                                       file_name='parity_plot_train',
                                       x_label='values',
                                       show_figure=False)

        self._save_split_data(df=X_train, filename='X_train', savepath=splitpath, columns=X_train.columns.values)
        self._save_split_data(df=X_test, filename='X_test', savepath=splitpath, columns=X_test.columns.values)
        self._save_split_data(df=y_train, filename='y_train', savepath=splitpath, columns='y_train')
        self._save_split_data(df=y_test, filename='y_test', savepath=splitpath, columns='y_test')
        self._save_split_data(df=y_pred, filename='y_pred', savepath=splitpath, columns='y_pred')
        self._save_split_data(df=y_pred_train, filename='y_pred_train', savepath=splitpath, columns='y_pred_train')

        # Save the fitted model, will be needed for DLHub upload later on
        joblib.dump(model, os.path.join(splitpath, str(model.model.__class__.__name__) + ".pkl"))
        return

    def _setup_savedir(self, model, selector, savepath):
        now = datetime.now()
        dirname = model.model.__class__.__name__+'_'+self.splitter+'_'+selector.__class__.__name__
        dirname = f"{dirname}_{now.month:02d}_{now.day:02d}" \
            f"_{now.hour:02d}_{now.minute:02d}_{now.second:02d}"
        if savepath == None:
            splitdir = os.getcwd()
        else:
            splitdir = os.path.join(savepath, dirname)
        if not os.path.exists(splitdir):
            os.mkdir(splitdir)
        return splitdir

    def _save_split_data(self, df, filename, savepath, columns):
        if type(df) == pd.core.frame.DataFrame:
            df.columns = columns
        if type(df) == pd.core.series.Series:
            df.name = columns
        df.to_excel(os.path.join(savepath, filename)+'.xlsx', index=False)
        return

    def _collect_data(self, filename, savepath):
        # Note this is only meant for collecting y-data (single column)
        dirs = [d for d in os.listdir(savepath) if 'split' in d]
        data = list()
        for d in dirs:
            try:
                data.append(np.array(pd.read_excel(os.path.join(savepath, os.path.join(d, filename)+'.xlsx'),
                                                   engine='openpyxl')[filename]))
            except:
                data.append(np.array(pd.read_excel(os.path.join(savepath, os.path.join(d, filename)+'.xlsx'))[filename]))
        data = pd.Series(np.concatenate(data).ravel())
        return data

    def help(self):
        print('Documentation for', self.splitter)
        pprint(dict(inspect.getmembers(self.splitter))['__doc__'])
        print('\n')
        print('Class methods for,', self.splitter)
        pprint(dict(inspect.getmembers(self.splitter, predicate=inspect.ismethod)))
        print('\n')
        print('Class attributes for,', self.splitter)
        pprint(self.splitter.__dict__)
        return


class SklearnDataSplitter(BaseSplitter):
    """
    Class to wrap any scikit-learn based data splitter, e.g. KFold

    Args:
        splitter (sklearn.model_selection object): a sklearn.model_selection object, e.g. sklearn.model_selection.KFold()
        kwargs : key word arguments for the sklearn.model_selection object, e.g. n_splits=5 for KFold()

    Methods:
        get_n_splits: method to calculate the number of splits to perform

            Args:
                None

            Returns:
                (int), number of train/test splits

        split: method to perform split into train indices and test indices

            Args:
                X: (numpy array), array of X features

            Returns:
                (numpy array), array of train and test indices

        _setup_savedir: method to create a savedir based on the provided model, splitter, selector names and datetime

            Args:
                model: (mastml.models.SklearnModel or other estimator object), an estimator, e.g. KernelRidge
                selector: (mastml.feature_selectors or other selector object), a selector, e.g. EnsembleModelFeatureSelector
                savepath: (str), string designating the savepath

            Returns:
                splitdir: (str), string containing the new subdirectory to save results to
    """

    def __init__(self, splitter, **kwargs):
        super(SklearnDataSplitter, self).__init__()
        self.splitter = getattr(sklearn.model_selection, splitter)(**kwargs)

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.splitter.get_n_splits()

    def split(self, X, y=None, groups=None):
        return self.splitter.split(X)

    def _setup_savedir(self, model, selector, savepath):
        now = datetime.now()
        dirname = model.model.__class__.__name__+'_'+self.splitter.__class__.__name__+'_'+selector.__class__.__name__
        dirname = f"{dirname}_{now.month:02d}_{now.day:02d}" \
            f"_{now.hour:02d}_{now.minute:02d}_{now.second:02d}"
        if savepath == None:
            splitdir = os.getcwd()
        else:
            splitdir = os.path.join(savepath, dirname)
        if not os.path.exists(splitdir):
            os.mkdir(splitdir)
        return splitdir


class NoSplit(BaseSplitter):
    """
    Class to just train the model on the training data and test it on that same data. Sometimes referred to as a "Full fit"
    or a "Single fit", equivalent to just plotting y vs. x.

    Args:
        None (only object instance)

    Methods:
        get_n_splits: method to calculate the number of splits to perform

            Args:
                None

            Returns:
                (int), always 1 as only a single split is performed

        split: method to perform split into train indices and test indices

            Args:
                X: (numpy array), array of X features

            Returns:
                (numpy array), array of train and test indices (all data used as train and test for NoSplit)

    """

    def __init__(self):
        super(NoSplit, self).__init__()

    def get_n_splits(self, X=None, y=None, groups=None):
        return 1

    def split(self, X, y=None, groups=None):
        indices = np.arange(X.shape[0])
        return [[indices, indices]]


class JustEachGroup(BaseSplitter):
    """
    Class to train the model on one group at a time and test it on the rest of the data
    This class wraps scikit-learn's LeavePGroupsOut with P set to n-1. More information is available at:
    http://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeavePGroupsOut.html

    Args:
        None (only object instance)

    Methods:
        get_n_splits: method to calculate the number of splits to perform

            Args:
                groups: (numpy array), array of group labels

            Returns:
                (int), number of unique groups, indicating number of splits to perform

        split: method to perform split into train indices and test indices

            Args:
                X: (numpy array), array of X features
                y: (numpy array), array of y data
                groups: (numpy array), array of group labels

            Returns:
                (numpy array), array of train and test indices

    """

    def __init__(self):
        super(JustEachGroup, self).__init__()

    def get_n_splits(self, X=None, y=None, groups=None):
        return np.unique(groups).shape[0]

    def split(self, X, y, groups):
        n_groups = self.get_n_splits(groups=groups)
        lpgo = ms.LeavePGroupsOut(n_groups=n_groups-1)
        trains_tests = list()
        for train_index, test_index in lpgo.split(X, y, groups):
            trains_tests.append((train_index, test_index))
        return trains_tests


class LeaveCloseCompositionsOut(BaseSplitter):
    """
    Leave-P-out where you exclude materials with compositions close to those the test set

    Computes the distance between the element fraction vectors. For example, the :math:`L_2`
    distance between Al and Cu is :math:`\sqrt{2}` and the :math:`L_1` distance between Al
    and Al0.9Cu0.1 is 0.2.

    Consequently, this splitter requires a list of compositions as the input to `split` rather
    than the features.

    Args:
        composition_df (pd.DataFrame): dataframe containing the vector of material compositions to analyze
        dist_threshold (float): Entries must be farther than this distance to be included in the
            training set
        nn_kwargs (dict): Keyword arguments for the scikit-learn NearestNeighbor class used
            to find nearest points
    """

    def __init__(self, composition_df, dist_threshold=0.1, nn_kwargs=None):
        super(LeaveCloseCompositionsOut, self).__init__()
        if nn_kwargs is None:
            nn_kwargs = {}
        self.composition_df = composition_df
        self.dist_threshold = dist_threshold
        self.nn_kwargs = nn_kwargs

    def split(self, X, y=None, groups=None):

        # Generate the composition vectors
        frac_computer = ElementFraction()
        elem_fracs = frac_computer.featurize_many(list(map(Composition, self.composition_df[self.composition_df.columns[0]])), pbar=False)

        # Generate the nearest-neighbor lookup tool
        neigh = NearestNeighbors(**self.nn_kwargs)
        neigh.fit(elem_fracs)

        # Generate a list of all entries
        all_inds = np.arange(0, self.composition_df.shape[0], 1)

        # Loop through each entry in X
        trains_tests = list()
        for i, x in enumerate(elem_fracs):

            # Get all the entries within the threshold distance of the test point
            too_close, = neigh.radius_neighbors([x], self.dist_threshold, return_distance=False)

            # Get the training set as "not these points"
            train_inds = np.setdiff1d(all_inds, too_close)
            test_inds = np.setdiff1d(all_inds, train_inds)

            trains_tests.append((np.asarray(train_inds), np.asarray(test_inds)))
        return trains_tests

    def get_n_splits(self, X=None, y=None, groups=None):
        return len(X)


class LeaveOutPercent(BaseSplitter):
    """
    Class to train the model using a certain percentage of data as training data

    Args:
        percent_leave_out (float): fraction of data to use in training (must be > 0 and < 1)

        n_repeats (int): number of repeated splits to perform (must be >= 1)

    Methods:
        get_n_splits: method to return the number of splits to perform

            Args:
                groups: (numpy array), array of group labels

            Returns:
                (int), number of unique groups, indicating number of splits to perform

        split: method to perform split into train indices and test indices

            Args:
                X: (numpy array), array of X features
                y: (numpy array), array of y data
                groups: (numpy array), array of group labels

            Returns:
                (numpy array), array of train and test indices

    """

    def __init__(self, percent_leave_out=0.2, n_repeats=5):
        super(LeaveOutPercent, self).__init__()
        self.percent_leave_out = percent_leave_out
        self.n_repeats = n_repeats

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_repeats

    def split(self, X, y=None, groups=None):
        indices = range(X.shape[0])
        split = list()
        for i in range(self.n_repeats):
            trains, tests = ms.train_test_split(indices, test_size=self.percent_leave_out, random_state=np.random.randint(1, 1000), shuffle=True)
            split.append((trains, tests))
        return split


class LeaveOutTwinCV(BaseSplitter):
    """
    Class to remove data twins from the test data.

    Args:
        threshold: (int), the threshold at which two data points are considered twins
        cv: A scikit-learn cross validation generator object to be used to create split # TODO idk if this is the same as "splitter" arg in SklearnDataSplitter
        allow_twins_in_train: (boolean), true if the twins should be allowed in training data but removed from the test sets, false if twins should just be removed altogether

    Methods:
        get_n_splits: method to calculate the number of splits to perform across all splitters

            Args:
                X: (numpy array), array of X features
                y: (numpy array), array of y data
                groups: (numpy array), array of group labels

            Returns:
                (int), the number 1 always

        split: method to perform split into train indices and test indices

            Args:
                X: (numpy array), array of X features
                y: (numpy array), array of y data
                groups: (numpy array), array of group labels

            Returns:
                (numpy array), array of train and test indices
    """

    def __init__(self, threshold, cv=None, allow_twins_in_train=True, **kwargs):
        self.threshold = int(threshold)
        if cv is None:
            self.cv = ms.RepeatedKFold()
        else:
            self.cv = getattr(sklearn.model_selection, cv)(**kwargs)
        self.allow_twins_in_train = allow_twins_in_train

    def _setup_savedir(self, model, selector, savepath):  # TODO stolen from SklearnDataSplitter
        now = datetime.now()
        dirname = model.model.__class__.__name__+'_'+self.cv.__class__.__name__+'_'+selector.__class__.__name__
        dirname = f"{dirname}_{now.month:02d}_{now.day:02d}" \
            f"_{now.hour:02d}_{now.minute:02d}_{now.second:02d}"
        if savepath == None:
            splitdir = os.getcwd()
        else:
            splitdir = os.path.join(savepath, dirname)
        if not os.path.exists(splitdir):
            os.mkdir(splitdir)
        return splitdir

    def get_n_splits(self, X=None, y=None, groups=None):
        return 1

    # TODO This is (mostly) just the old method copy and pasted, with depricated parts removed
    def split(self, X, y, X_noinput=None, path="/", groups=None):
        # intialize variables
        distances = []
        i = 0
        j = 0
        count = 0

        # calculate distances between every combination of items in X
        for a in X.T.iteritems():
            for b in X.T.iteritems():
                if j > i:
                    diff = np.linalg.norm(a[1] - b[1])
                    distances.append([diff, a[0], b[0]])
                j += 1
            i += 1
            j = 0

        # identifies the datapoints within the threshold
        distances = sorted(distances, key=lambda x: x[0])

        def find_nearest_index(array, value):
            for idx, n in enumerate(array):
                if (n[0] >= value):
                    return idx
            return 0
        x = find_nearest_index(distances, self.threshold)
        removed = distances[:x]

        distances = pd.DataFrame(distances, columns=['dist', 'a', 'b'])

        # create X and y with twins removed
        X_notwin = X.copy()
        y_notwin = y.copy()

        if not self.allow_twins_in_train:
            # remove all twins in both X and y
            if (len(removed) != 0):
                for i in removed:
                    if (i[1] in X_notwin.index):
                        X_notwin = X_notwin.drop(i[1], inplace=False)
                    if (i[2] in X_notwin.index):
                        X_notwin = X_notwin.drop(i[2], inplace=False)
                    if (i[1] in y_notwin.index):
                        y_notwin = y_notwin.drop(i[1], inplace=False)
                    if (i[2] in y_notwin.index):
                        y_notwin = y_notwin.drop(i[2], inplace=False)

        # generate splits from chosen cv (cross validator)
        splits_generator = self.cv.split(X_notwin, y_notwin)

        # change splits into list form so it can be mutated
        splits = list()
        for split in splits_generator:
            splits.append(list(split))

        if self.allow_twins_in_train:
            # remove from test sets
            if (len(removed) != 0):
                for split in splits:
                    # orig_size = len(split[1])
                    for i in removed:
                        if (i[1] in split[1]):
                            split[1] = [x for x in split[1] if x != i[1]]
        else:
            # change the split's relative indices to old indices, because called split on data with indicies removed
            old_index = X_notwin.index
            for split in splits:
                for idx, val in enumerate(split[0]):
                    split[0][idx] = old_index[idx]
                for idx, val in enumerate(split[1]):
                    split[1][idx] = old_index[idx]

        return splits


class Bootstrap(BaseSplitter):
    """
    # Note: Bootstrap taken directly from sklearn Github (https://github.com/scikit-learn/scikit-learn/blob/0.11.X/sklearn/cross_validation.py)
    # which was necessary as it was later removed from more recent sklearn releases
    Random sampling with replacement cross-validation iterator
    Provides train/test indices to split data in train test sets
    while resampling the input n_bootstraps times: each time a new
    random split of the data is performed and then samples are drawn
    (with replacement) on each side of the split to build the training
    and test sets.
    Note: contrary to other cross-validation strategies, bootstrapping
    will allow some samples to occur several times in each splits. However
    a sample that occurs in the train split will never occur in the test
    split and vice-versa.
    If you want each sample to occur at most once you should probably
    use ShuffleSplit cross validation instead.

    Args:
        n : int
            Total number of elements in the dataset.
        n_bootstraps : int (default is 3)
            Number of bootstrapping iterations
        train_size : int or float (default is 0.5)
            If int, number of samples to include in the training split
            (should be smaller than the total number of samples passed
            in the dataset).
            If float, should be between 0.0 and 1.0 and represent the
            proportion of the dataset to include in the train split.
        test_size : int or float or None (default is None)
            If int, number of samples to include in the training set
            (should be smaller than the total number of samples passed
            in the dataset).
            If float, should be between 0.0 and 1.0 and represent the
            proportion of the dataset to include in the test split.
            If None, n_test is set as the complement of n_train.
        random_state : int or RandomState
            Pseudo number generator state used for random sampling.

    """

    # Static marker to be able to introspect the CV type
    indices = True

    def __init__(self, n, n_bootstraps=3, train_size=.5, test_size=None,
                 n_train=None, n_test=None, random_state=0):
        super(Bootstrap, self).__init__()
        self.n = n
        self.n_bootstraps = n_bootstraps
        if n_train is not None:
            train_size = n_train
            warnings.warn(
                "n_train is deprecated in 0.11 and scheduled for "
                "removal in 0.12, use train_size instead",
                DeprecationWarning, stacklevel=2)
        if n_test is not None:
            test_size = n_test
            warnings.warn(
                "n_test is deprecated in 0.11 and scheduled for "
                "removal in 0.12, use test_size instead",
                DeprecationWarning, stacklevel=2)
        if (isinstance(train_size, float) and train_size >= 0.0 and train_size <= 1.0):
            self.train_size = ceil(train_size * n)
        elif isinstance(train_size, int):
            self.train_size = train_size
        else:
            raise ValueError("Invalid value for train_size: %r" %
                             train_size)
        if self.train_size > n:
            raise ValueError("train_size=%d should not be larger than n=%d" %
                             (self.train_size, n))

        if (isinstance(test_size, float) and test_size >= 0.0 and test_size <= 1.0):
            self.test_size = ceil(test_size * n)
        elif isinstance(test_size, int):
            self.test_size = test_size
        elif test_size is None:
            self.test_size = self.n - self.train_size
        else:
            raise ValueError("Invalid value for test_size: %r" % test_size)
        if self.test_size > n:
            raise ValueError("test_size=%d should not be larger than n=%d" %
                             (self.test_size, n))

        self.random_state = random_state

    def __iter__(self):
        rng = check_random_state(self.random_state)
        for i in range(self.n_bootstraps):
            # random partition
            permutation = rng.permutation(self.n)
            ind_train = permutation[:self.train_size]
            ind_test = permutation[self.train_size:self.train_size
                                   + self.test_size]

            # bootstrap in each split individually
            train = rng.randint(0, self.train_size,
                                size=(self.train_size,))
            test = rng.randint(0, self.test_size,
                               size=(self.test_size,))
            yield ind_train[train], ind_test[test]

    def __repr__(self):
        return ('%s(%d, n_bootstraps=%d, train_size=%d, test_size=%d, '
                'random_state=%d)' % (
                    self.__class__.__name__,
                    self.n,
                    self.n_bootstraps,
                    self.train_size,
                    self.test_size,
                    self.random_state,
                ))

    def __len__(self):
        return self.n_bootstraps

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.__len__()

    def split(self, X, y=None, groups=None):
        indices = range(X.shape[0])
        split = list()
        for trains, tests in self:
            split.append((trains.tolist(), tests.tolist()))
        return split
