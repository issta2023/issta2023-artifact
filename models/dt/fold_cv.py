
from sklearn.linear_model import LogisticRegression as LogReg
from sklearn.model_selection import StratifiedKFold
import numpy as np
from sklearn.metrics import accuracy_score
import copy

def my_cv(

    X,
    s,
    clf=LogReg(multi_class='auto', solver='lbfgs'),
    cv_n_folds=5,
    seed=None,
):
    """Estimates P(s,y), the confident counts of the latent
    joint distribution of true and noisy labels
    using observed s and predicted probabilities psx.

    The output of this function is a numpy array of shape (K, K).

    Under certain conditions, estimates are exact, and in many
    conditions, estimates are within one percent of actual.

    Notes: There are two ways to compute the confident joint with pros/cons.
    1. For each holdout set, we compute the confident joint, then sum them up.
    2. Compute pred_proba for each fold, combine, compute the confident joint.
    (1) is more accurate because it correctly computes thresholds for each fold
    (2) is more accurate when you have only a little data because it computes
    the confident joint using all the probabilities. For example if you had 100
    examples, with 5-fold cross validation + uniform p(y) you would only have 20
    examples to compute each confident joint for (1). Such small amounts of data
    is bound to result in estimation errors. For this reason, we implement (2),
    but we implement (1) as a commented out function at the end of this file.

    Parameters
    ----------
    X : np.array
      Input feature matrix (N, D), 2D numpy array

    s : np.array
        A discrete vector of labels, s, which may contain mislabeling. "s"
        denotes the noisy label instead of \tilde(y), for ASCII reasons.

    clf : sklearn.classifier or equivalent
      Default classifier used is logistic regression. Assumes clf
      has predict_proba() and fit() defined.

    cv_n_folds : int
      The number of cross-validation folds used to compute
      out-of-sample probabilities for each example in X.

    thresholds : iterable (list or np.array) of shape (K, 1)  or (K,)
      P(s^=k|s=k). If an example has a predicted probability "greater" than
      this threshold, it is counted as having hidden label y = k. This is
      not used for pruning, only for estimating the noise rates using
      confident counts. This value should be between 0 and 1. Default is None.

    seed : int (default = None)
        Set the default state of the random number generator used to split
        the cross-validated folds. If None, uses np.random current random state.

    calibrate : bool (default: True)
        Calibrates confident joint estimate P(s=i, y=j) such that
        np.sum(cj) == len(s) and np.sum(cj, axis = 1) == np.bincount(s).

    Returns
    ------
      Returns a tuple of two numpy array matrices in the form:
      (joint counts matrix, predicted probability matrix)"""

    # Number of classes
    K = len(np.unique(s))

    # Ensure labels are of type np.array()
    s = np.asarray(s)

    # Create cross-validation object for out-of-sample predicted probabilities.
    # CV folds preserve the fraction of noisy positive and
    # noisy negative examples in each class.
    kf = StratifiedKFold(n_splits=cv_n_folds, shuffle=True, random_state=seed)

    # Intialize psx array
    psx = np.zeros((len(s), K))

    # Split X and s into "cv_n_folds" stratified folds.
    for k, (cv_train_idx, cv_holdout_idx) in enumerate(kf.split(X, s)):

        clf_copy = copy.deepcopy(clf)

        # Select the training and holdout cross-validated sets.
        # X_train_cv, X_holdout_cv = X[cv_train_idx], X[cv_holdout_idx]
        # s_train_cv, s_holdout_cv = s[cv_train_idx], s[cv_holdout_idx]

        # Fit the clf classifier to the training set and
        # predict on the holdout set and update psx.
        
        
        clf_copy.fit(cv_train_idx, cv_train_idx)
        psx_cv = clf_copy.predict_proba(cv_holdout_idx)  # P(s = k|x) # [:,1]
        # pred = np.argmax(psx_cv, axis=1)
        # s_cv = s[cv_holdout_idx]

        # print(np.sum(pred==s_cv))
        # print(cv_holdout_idx)
        # idxs = []
        # for idx in X[cv_holdout_idx]:
        #     idxs.append(idx[3])
        # print(idxs)
        psx[cv_holdout_idx] = psx_cv
        holdout_label = s[cv_holdout_idx]
        holdout_pre = psx[cv_holdout_idx]
        break

    # pred = np.argmax(psx, axis = 1)
    holdout_pred = np.argmax(holdout_pre, axis = 1)
    accuracy = accuracy_score(holdout_label, holdout_pred)

   


    return accuracy
