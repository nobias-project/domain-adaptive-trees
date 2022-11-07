import numpy as np
import math
import yapftests.yapf_test
from scipy import stats
import pandas as pd
from typing import Dict, List, Tuple
from pandas import DataFrame, Series


class DecisionTreeClassifier(object):
    def __init__(self, max_depth: int, *args, **kwargs):
        self.max_depth = max_depth
        self.depth = 0
        self.min_cases = 5
        self.cat = None
        self.tree = None

        self._you_are_here = ()
        self._current_path = []
        self.running_da_cov_shift = False  # covariate shift
        self.running_da_con_shift = False  # concept shift
        self.alpha = 0.5
        self.X_td = None
        self.y_td = None

        self.y_values = None  # values are based on the source domain todo: might have to delete

    def fit(self, X: DataFrame, y: Series, cat_atts: List[str] = None,
            alpha: float = None, X_td: object = None, y_td: object = None, ):
        # instance-specific params
        cat = [] if cat_atts is None else cat_atts
        self.cat = set(cat)
        self.y_values = y.value_counts().index.to_list()
        # domain adaptation params
        if X_td is not None:
            self.running_da_cov_shift = True
        if X_td is not None and y_td is not None:
            self.running_da_con_shift = True
        self.alpha = alpha if alpha is not None else alpha
        self.X_td = X_td if X_td is not None else X_td
        self.y_td = y_td if y_td is not None else y_td
        # build tree
        self.tree, self.depth = self.build(X, y, depth=0)

    def build(self, X: DataFrame, y: Series, depth: int):
        """
        X: Feature set
        y: target variable
        depth: the depth of the current layer
        """
        leny = len(y)
        print('.', depth, leny)
        # base case 2: no data in this group
        if leny == 0:
            print('all the same')
            return None, 0
        # base case 3: all y is the same in this group
        if self.all_same(y):
            return {'type': 'leaf',
                    'val': y.iloc[0], 'tot': leny, 'dist': y.value_counts(sort=False) / leny}, 0
        # base case 4: max depth reached
        if depth >= self.max_depth:
            return {'type': 'leaf',
                    'val': stats.mode(y).mode[0], 'tot': leny, 'dist': y.value_counts(sort=False) / leny}, 0
        # recursive case:
        col, cutoff, gain = self.find_best_split_of_all(X, y)  # find one split given an information gain
        if col is None:  # no split improves
            return {'type': 'leaf',
                    'val': stats.mode(y).mode[0], 'tot': leny, 'dist': y.value_counts(sort=False) / leny}, 0
        if col in self.cat:  # split for cont. vars; all-but for cat. vars
            cond = X[col] == cutoff
        else:
            cond = X[col] < cutoff
        X_left = X[cond]    # < value
        X_right = X[~cond]  # >= value
        y_left = y[cond]    # left hand side data
        y_right = y[~cond]  # right hand side data
        print('split', col, gain, cutoff)
        par_node = {'type': 'split',
                    'gain': gain, 'split_col': col, 'cutoff': cutoff, 'tot': leny, 'dist': y.value_counts(sort=False) / leny}

        # the beauty of recursion (?)
        prev_path = self._current_path.copy()
        print(prev_path)
        # generate tree for the left hand side data
        self._you_are_here = (col, cutoff, 'left')
        print(self._you_are_here)
        self._current_path = prev_path + [self._you_are_here]
        print(self._current_path)
        par_node['left'], dleft = self.build(X_left, y_left, depth + 1)

        # generate tree for the right hand side data
        self._you_are_here = (col, cutoff, 'right')
        print(self._you_are_here)
        self._current_path = prev_path + [self._you_are_here]
        print(self._current_path)
        par_node['right'], dright = self.build(X_right, y_right, depth + 1)

        return par_node, max(dleft, dright) + 1

    # # todo
    # def _store_subtree(self, par_node: Dict):
    #     if par_node is None:
    #         print('no data in this group')
    #         return None
    #     else:
    #         # return `split` info
    #         if par_node['type'] == 'split':
    #             if par_node['split_col'] in self.cat:
    #                 l_rule = '== {cutoff}'.format(cutoff=par_node['cutoff'])
    #                 r_rule = '!= {cutoff}'.format(cutoff=par_node['cutoff'])
    #             else:
    #                 l_rule = '< {cutoff}'.format(cutoff=par_node['cutoff'])
    #                 r_rule = '>= {cutoff}'.format(cutoff=par_node['cutoff'])
    #             sub_tree = {'type': par_node['type'],
    #                         'split_col': par_node['split_col'],
    #                         'cutoff': par_node['cutoff'],
    #                         'lhs': l_rule, 'rhs': r_rule}
    #         # return `leaf` info
    #         else:
    #             sub_tree = {'type': par_node['type']}
    #     return sub_tree

    # todo
    # def _get_current_path(self):
    #     current_path = []
    #     while self.you_are_here[0] > 0:
    #         prev_layer = self.you_are_here[0] - 1

    @staticmethod
    def all_same(items):
        return all(x == items.iloc[0] for x in items)

    def find_best_split_of_all(self, X: DataFrame, y: Series):

        if len(self._you_are_here) > 0:
            print("you're at the {side} of {col}".format(side=self._you_are_here[2], col=self._you_are_here[0]))

        # you_are_here = (att: str, cutoff, side: str) todo: function handle X_td as dataframe, list, etc...
        if self.running_da_con_shift:
            if len(self._you_are_here) == 1:
                # root node
                y_td = self.y_td.copy()
                X_td = self.X_td.copy()
            else:
                print(self._you_are_here)
                y_td = self.y_td.copy()
                X_td = self.X_td.copy()

                # all other nodes
                # current_path = self.get_current_path() todo

                # if self.you_are_here[1] in self.cat:
                #     cond = self.X_td[self.you_are_here[1]] == self.you_are_here[2]
                # else:
                #     cond = self.X_td[self.you_are_here[1]] < self.you_are_here[2]
                # if self.you_are_here[3] == 'lhs':
                #     y_td = self.y_td[cond].copy()
                #     X_td = self.X_td[cond].copy()
                # else:  # self.you_are_here[3] == 'rhs'
                #     y_td = self.y_td[~cond].copy()
                #     X_td = self.X_td[~cond].copy()
        else:
            y_td = None
            X_td = None
        ###

        best_gain = 0
        best_col = None
        best_cutoff = None
        for c in X.columns:
            is_cat = c in self.cat
            if self.running_da_con_shift:
                gain, cur_cutoff = self.da_find_best_split_attribute(X[c], y, is_cat, X_td[c], y_td, self.alpha)
            else:
                gain, cur_cutoff = self.find_best_split_attribute(X[c], y, is_cat)
            if gain > best_gain:
                best_gain = gain
                best_cutoff = cur_cutoff
                best_col = c
        return best_col, best_cutoff, best_gain

    def find_best_split_attribute(self, x: Series, y: Series, is_cat: bool):
        best_gain = 0
        best_cutoff = None
        if is_cat:
            values = x.unique()
        else:
            values = np.sort(x.unique())
        # get entropy H(T)
        entropy_total = self.info(y)
        n_tot = len(x)
        for value in values:
            cond = x == value if is_cat else x < value
            n_left = sum(cond)
            if n_left < self.min_cases:
                continue
            n_right = n_tot - n_left
            if n_right < self.min_cases:
                continue
            # get entropy H(T|A=a)
            entropy_left = self.info(y[cond])    # < value
            entropy_right = self.info(y[~cond])  # >= value
            left_prop = n_left / n_tot
            right_prop = 1 - left_prop
            # Information Gain: H(T) - H(T|A=a)
            gain = entropy_total - left_prop * entropy_left - right_prop * entropy_right
            if gain > best_gain:
                best_gain = gain
                best_cutoff = value
        return best_gain, best_cutoff

    def da_find_best_split_attribute(self, x: Series, y: Series, is_cat: bool, x_td: Series, y_td: Series, alpha: float):
        best_gain = 0
        best_cutoff = None
        if is_cat:
            values = x.unique()
        else:
            values = np.sort(x.unique())
        # get entropy H(T)
        entropy_total = self.da_info(self.y_values, y, y_td, alpha)
        n_tot = len(x)
        for value in values:
            cond = x == value if is_cat else x < value
            cond_for_td = x_td == value if is_cat else x_td < value  # index must align for x_td and y_td
            n_left = sum(cond)
            if n_left < self.min_cases:
                continue
            n_right = n_tot - n_left
            if n_right < self.min_cases:
                continue
            # get entropy H(T|A=a)
            entropy_left = self.da_info(self.y_values, y[cond], y_td[cond_for_td], self.alpha)     # < value
            entropy_right = self.da_info(self.y_values, y[~cond], y_td[~cond_for_td], self.alpha)  # >= value
            left_prop = n_left / n_tot
            right_prop = 1 - left_prop
            # Information Gain: H(T) - H(T|A=a)
            gain = entropy_total - left_prop * entropy_left - right_prop * entropy_right
            if gain > best_gain:
                best_gain = gain
                best_cutoff = value
        return best_gain, best_cutoff

    @staticmethod
    def info(y: Series):
        vc = y.value_counts()
        tot = len(y)
        ent = 0
        for v in vc:
            prop = v / tot
            ent -= prop * math.log2(prop)
        return ent

    @staticmethod
    def da_info(y_values: List[int], y_source: Series, y_target: Series, alpha: float):  # todo: da_info for X_td only
        # source domain
        vc_s = y_source.value_counts()
        tot_s = len(y_source)
        # target domain
        vc_t = y_target.value_counts()
        tot_t = len(y_target)
        # domain-adaptive entropy
        ent = 0
        for val in y_values:  # the values are the (potential) index in value_count
            if val in vc_s.index:
                prop_s = vc_s[val] / tot_s
            else:
                prop_s = 0.0
            if val in vc_t.index:
                prop_t = vc_t[val] / tot_t
            else:
                prop_t = 0.0
            da_prop = (alpha * prop_s + (1 - alpha) * prop_t)
            if da_prop > 0.0:
                ent -= da_prop * math.log2(da_prop)
        return ent

    def predict(self, X):
        # results = np.array([0]*len(X))
        # results = pd.DataFrame(columns=['pred', 'prob'])
        results = pd.DataFrame({'prediction': pd.Series([], dtype='float'),
                                'probability': pd.Series([], dtype='float')})
        for i, r in enumerate(X.itertuples(index=False)):
            results.loc[i] = self._get_prediction(X.iloc[i])
        return results

    def _get_prediction(self, row):
        cur_layer = self.tree
        while cur_layer.get('cutoff'):
            col = cur_layer['split_col']
            cutoff = cur_layer['cutoff']
            is_cat = col in self.cat
            left = row[col] == cutoff if is_cat else row[col] < cutoff
            cur_layer = cur_layer['left'] if left else cur_layer['right']
        else:
            return [cur_layer.get('val'), cur_layer.get('dist')]

#
# EOF
#
