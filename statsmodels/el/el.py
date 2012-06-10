"""
Empirical Likelihood Implementation

Start: 21 May 2012
Last Updated: 7 June 2012

General References:

Owen, A. (2001). "Empirical Likelihood." Chapman and Hall



"""
import numpy as np
from scipy import optimize
from scipy.stats import chi2
from matplotlib import pyplot as plt
import itertools


class ElModel(object):
    """


    Initializes data for empirical likelihood.  Not intended for end user
    """

    def __init__(self, endog):
        self.endog = endog
        self.nobs = float(endog.shape[0])
        self.weights = np.ones(self.nobs) / float(self.nobs)
        if endog.ndim == 1:
            self.endog = self.endog.reshape(self.nobs, 1)
        # For now, self. weights should always be a vector of 1's and a
        # variable "new weights" should be created everytime weights are
        # changed.


class OptFuncts(ElModel):
    """


    A class that holds functions that are optimized/solved.  Not
    intended for the end user.
    """

    def __init__(self, endog):
        super(OptFuncts, self).__init__(endog)

    def get_j_y(self, eta1):
        """
        Calculates J and y via the log*' and log*''.

        Maximizing log* is done via sequential regression of
        y on J.

        See Owen pg. 63

        """

        data = np.copy(self.est_vect.T)
        data_star_prime = np.copy((1 + np.dot(eta1, data)))
        data_star_doub_prime = np.copy((1 + np.dot(eta1, data)))
        for elem in range(int(self.nobs)):
            if data_star_prime[0, elem] <= 1 / self.nobs:
                data_star_prime[0, elem] = 2 * self.nobs - \
                  (self.nobs) ** 2 * data_star_prime[0, elem]
            else:
                data_star_prime[0, elem] = 1. / data_star_prime[0, elem]
            if data_star_doub_prime[0, elem] <= 1 / self.nobs:
                data_star_doub_prime[0, elem] = - self.nobs ** 2
            else:
                data_star_doub_prime[0, elem] = \
                  - (data_star_doub_prime[0, elem]) ** -2
        data_star_prime = data_star_prime.reshape(self.nobs, 1)
        data_star_doub_prime = data_star_doub_prime.reshape(self.nobs, 1)
        J = ((- 1 * data_star_doub_prime) ** .5) * self.est_vect
        y = data_star_prime / ((- 1 * data_star_doub_prime) ** .5)
        return J, y

    def modif_newton(self,  x0):
        """
        Modified Newton's method for maximizing the log* equation.

        See Owen pg. 64

        """
        params = x0.reshape(1, self.est_vect.shape[1])
        diff = 1
        while diff > 10 ** (-10):
            new_J = np.copy(self.get_j_y(params)[0])
            new_y = np.copy(self.get_j_y(params)[1])
            inc = np.dot(np.linalg.pinv(new_J), \
                         new_y).reshape(1, self.est_vect.shape[1])
            new_params = np.copy(params + inc)
            diff = np.sum(np.abs(params - new_params))
            params = np.copy(new_params)
            print params
            if np.any(params > 10 ** 10) \
              or np.any(params < - (10 ** 10)):
                raise Exception('Optimization Failed')
        return params

    def find_eta(self, eta):

        """
        Finding the root of sum(xi-h0)/(1+eta(xi-mu)) solves for
        eta when computing ELR for univariate mean.

        See Owen (2001) pg 22.  (eta is his lambda to avoid confusion
        with the built-in lambda.

        """
        return np.sum((self.data - self.mu0) / \
              (1. + eta * (self.data - self.mu0)))

    def ci_limits_mu(self, mu_test):
        return self.hy_test_mean(mu_test)[1] - self.r0

    def find_gamma(self, gamma):

        """
        Finds gamma that satisfies
        sum(log(n * w(gamma))) - log(r0) = 0

        Used for confidence intervals for the mean.

        See Owen (2001) pg. 23.

        """

        denom = np.sum((self.endog - gamma) ** -1)
        new_weights = (self.endog - gamma) ** -1 / denom
        return -2 * np.sum(np.log(self.nobs * new_weights)) - \
            self.r0

    def opt_var(self, nuisance_mu, pval=False):
        """

        This is the function to be optimized over a nuisance mean parameter
        to determine the likelihood ratio for the variance.  In this function
        is the Newton optimization that finds the optimal weights given
        a mu parameter and sig2_0.

        Also, it contains the creating of self.est_vect (short for estimating
        equations vector).  That then gets read by the log-star equations.

        Not intended for end user.

        """

        sig_data = ((self.endog - nuisance_mu) ** 2 \
                    - self.sig2_0)
        mu_data = (self.endog - nuisance_mu)
        self.est_vect = np.concatenate((mu_data, sig_data), axis=1)
        eta_star = self.modif_newton(np.array([1 / self.nobs,
                                               1 / self.nobs]))
        denom = 1 + np.dot(eta_star, self.est_vect.T)
        self.new_weights = 1 / self.nobs * 1 / denom
        llr = np.sum(np.log(self.nobs * self.new_weights))
        if pval:  # Used for contour plotting
            return 1 - chi2.cdf(-2 * llr, 1)
        return -2 * llr

    def  ci_limits_var(self, var_test):
        """

        Used to determine the confidence intervals for the variance.
        It calls hy_test_var and when called by an optimizer,
        finds the value of sig2_0 that is chi2.ppf(significance-level)

        """

        return self.hy_test_var(var_test)[1] - self.r0

    def opt_skew(self, nuis_params):
        """

        Called by hy_test_skew.  This function is optimized over
        nuisance parameters mu and sigma

        """
        mu_data = self.endog - nuis_params[0]
        sig_data = ((self.endog - nuis_params[0]) ** 2) - nuis_params[1]
        skew_data = ((((self.endog - nuis_params[0]) ** 3) / \
                    (nuis_params[1] ** 1.5))) - self.skew0
        self.est_vect = np.concatenate((mu_data, sig_data, skew_data), \
                                       axis=1)
        eta_star = self.modif_newton(np.array([1 / self.nobs,
                                               1 / self.nobs,
                                               1 / self.nobs]))
        denom = 1 + np.dot(eta_star, self.est_vect.T)
        self.new_weights = 1 / self.nobs * 1 / denom
        llr = np.sum(np.log(self.nobs * self.new_weights))
        return -2 * llr

    def opt_kurt(self, nuis_params):
        """

        Called by hy_test_kurt.  This function is optimized over
        nuisance parameters mu and sigma

        """
        mu_data = self.endog - nuis_params[0]
        sig_data = ((self.endog - nuis_params[0]) ** 2) - nuis_params[1]
        kurt_data = (((((self.endog - nuis_params[0]) ** 4) / \
                    (nuis_params[1] ** 2))) - 3) - self.kurt0
        self.est_vect = np.concatenate((mu_data, sig_data, kurt_data), \
                                       axis=1)
        eta_star = self.modif_newton(np.array([1 / self.nobs,
                                               1 / self.nobs,
                                               1 / self.nobs]))
        denom = 1 + np.dot(eta_star, self.est_vect.T)
        self.new_weights = 1 / self.nobs * 1 / denom
        llr = np.sum(np.log(self.nobs * self.new_weights))
        return -2 * llr


class DescStat(OptFuncts):
    """


    A class for confidence intervals and hypothesis tests invovling mean,
    variance and covariance.

    Parameters
    ----------
    endog: 1-D array
        Data to be analyzed
    """

    def __init__(self, endog):
        super(DescStat, self).__init__(endog)

    def hy_test_mean(self, mu0,  trans_data=None, print_weights=False):

        """
        Returns the p-value, -2 * log-likelihood ratio and weights
        for a hypothesis test of the means.

        Parameters
        ----------
        mu0: Mean under the null hypothesis

        print_weights: If print_weights = True the funtion returns
        the weight of the observations under the null hypothesis
        | default = False

        """
        self.mu0 = mu0
        if trans_data  is None:
            self.data = self.endog
        else:
            self.data = trans_data
        eta_min = (1 - (1 / self.nobs)) / (self.mu0 - max(self.data))
        eta_max = (1 - (1 / self.nobs)) / (self.mu0 - min(self.data))
        eta_star = optimize.brentq(self.find_eta, eta_min, eta_max)
        new_weights = (1 / self.nobs) * \
            1. / (1 + eta_star * (self.data - self.mu0))
        llr = -2 * np.sum(np.log(self.nobs * new_weights))
        if print_weights:
            return 1 - chi2.cdf(llr, 1), llr, new_weights
        else:
            return 1 - chi2.cdf(llr, 1), llr

    def ci_mean(self, sig=.05, method='nested-brent', epsilon=10 ** -6,
                 gamma_low=-10 ** 10, gamma_high=10 ** 10, \
                 tol=10 ** -6):

        """
        Returns the confidence interval for the mean.

        Parameters
        ----------
        sig: Significance level | default=.05

        Optional
        --------

        method: Root finding method,  Can be 'nested-brent or gamma'.
            default | gamma

            'gamma' Tries to solve for the gamma parameter in the
            Lagrangian (see Owen pg 22) and then determine the weights.

            'nested brent' uses brents method to find the confidence
            intervals but must maximize the likelihhod ratio on every
            iteration.

            'bisect' is similar to the nested-brent but instead it
            is a brent nested in a bisection algorithm.

            gamma is much faster.  If the optimizations does not,
            converge, try expanding the gamma_high and gamma_low
            variable.

        gamma_low: lower bound for gamma when finding lower limit.
            If function returns f(a) and f(b) must have different signs,
            consider lowering gamma_low. default | gamma_low =-(10**10)

        gamma_high: upper bound for gamma when finding upper limit.
            If function returns f(a) and f(b) must have different signs,
            consider raising gamma_high. default |gamma_high=10**10

        epsilon: When using 'nested-brent', amount to decrease (increase)
            from the maximum (minimum) of the data when
            starting the search.  This is to protect against the
            likelihood ratio being zero at the maximum (minimum)
            value of the data.  If data is very small in absolute value
            (<10 ** -6) consider shrinking epsilon

            When using 'gamma' amount to decrease (increase) the
            minimum (maximum) by to start the search for gamma.
            If fucntion returns f(a) and f(b) must have differnt signs,
            consider lowering epsilon.

            default| epsilon=10**-6

        tol: Tolerance for the likelihood ratio in the bisect method.
            default | tol=10**-6

        """

        sig = 1 - sig
        if method == 'nested-brent':
            self.r0 = chi2.ppf(sig, 1)
            middle = np.mean(self.endog)
            epsilon_u = (max(self.endog) - np.mean(self.endog)) * epsilon
            epsilon_l = (np.mean(self.endog) - min(self.endog)) * epsilon
            ul = optimize.brentq(self.ci_limits_mu, middle,
                max(self.endog) - epsilon_u)
            ll = optimize.brentq(self.ci_limits_mu, middle,
                min(self.endog) + epsilon_l)
            return  ll, ul

        if method == 'gamma':
            self.r0 = chi2.ppf(sig, 1)
            gamma_star_l = optimize.brentq(self.find_gamma, gamma_low,
                min(self.endog) - epsilon)
            gamma_star_u = optimize.brentq(self.find_gamma, \
                         max(self.endog) + epsilon, gamma_high)
            weights_low = ((self.endog - gamma_star_l) ** -1) / \
                np.sum((self.endog - gamma_star_l) ** -1)
            weights_high = ((self.endog - gamma_star_u) ** -1) / \
                np.sum((self.endog - gamma_star_u) ** -1)
            mu_low = np.sum(weights_low * self.endog)
            mu_high = np.sum(weights_high * self.endog)
            return mu_low,  mu_high

        if method == 'bisect':
            self.r0 = chi2.ppf(sig, 1)
            self.mu_high = self.endog.mean()
            mu_hmax = max(self.endog)
            while abs(self.hy_test_mean(self.mu_high)[1]
                 - self.r0) > tol:
                self.mu_test = (self.mu_high + mu_hmax) / 2
                if self.hy_test_mean(self.mu_test)[1] - self.r0 < 0:
                    self.mu_high = self.mu_test
                else:
                    mu_hmax = self.mu_test

            self.mu_low = self.endog.mean()
            mu_lmin = min(self.endog)
            while abs(self.hy_test_mean(self.mu_low)[1]
                 - self.r0) > tol:
                self.mu_test = (self.mu_low + mu_lmin) / 2
                if self.hy_test_mean(self.mu_test)[1] - self.r0 < 0:
                    self.mu_low = self.mu_test
                else:
                    mu_lmin = self.mu_test
            return self.mu_low, self.mu_high

    def hy_test_var(self, sig2_0, print_weights=False):
        """

        Returns the p-value and -2 * log-likelihoog ratio for the
            hypothesized variance.

        Parameters
        ----------

        sig2_0: Hypothesized value to be tested

        Optional
        --------

        print_weights: If True, returns the weights that maximize the
            likelihood of observing sig2_0. default | False.


        Example
        -------
        random_numbers = np.random.standard_normal(1000)*100
        el_analysis = el.DescStat(random_numbers)
        hyp_test = el_analysis.hy_test_var(9500)


        """

        self.sig2_0 = sig2_0
        mu_max = max(self.endog)
        mu_min = min(self.endog)
        llr = optimize.fminbound(self.opt_var, mu_min, mu_max, \
                                 full_output=1)[1]
        p_val = 1 - chi2.cdf(llr, 1)
        if print_weights:
            return p_val, llr, self.new_weights
        else:
            return p_val, llr

    def ci_var(self, lower_bound=None, upper_bound=None, sig=.05):
        """

        Returns the confidence interval for the variance.

        Parameters
        ----------

        lower_bound: The minimum value the lower confidence interval can
        take on. The p-value from hy_test_var(lower_l) must be lower
        than 1 - significance level. default | calibrated at the .01
        significance level, asusming normality.


        upper_bound: The maximum value the upper confidence interval
        can take. The p-value from hy_test_var(upper_h) must be lower
        than 1 - significance level.  default | calibrated at the .01
        significance level, asusming normality.


        sig: The significance level for the conficence interval.
        default | .05


        Example
        -------
        random_numbers = np.random.standard_normal(100)
        el_analysis = el.DescStat(random_numbers)
        # Initialize El
        el_analysis.ci_var()
        >>>f(a) and f(b) must have different signs
        el_analysis.ci_var(.5, 2)
        # Searches for confidence limits where the lower limit > .5
        # and the upper limit <2.

        Troubleshooting Tips
        --------------------

        If the function returns the error f(a) and f(b) must have
        different signs, consider lowering lower_bound and raising
        upper_bound.

        If function returns 'Optimization Failed', consider narrowing the
        search area.

        """

        if upper_bound is not None:
            ul = upper_bound
        else:
            ul = ((self.nobs - 1) * self.endog.var()) / \
              (chi2.ppf(.0001, self.nobs - 1))
            print 'ul is', ul
        if lower_bound is not None:
            ll = lower_bound
        else:
            ll = ((self.nobs - 1) * self.endog.var()) / \
              (chi2.ppf(.9999, self.nobs - 1))
            print 'll is', ll
        sig = 1 - sig
        self.r0 = chi2.ppf(sig, 1)
        ll = optimize.brentq(self.ci_limits_var, ll, self.endog.var())
        ul = optimize.brentq(self.ci_limits_var, self.endog.var(), ul)
        return   ll, ul

    def var_p_plot(self, lower, upper, step, sig=.05):
        """

        Plots the p-values of the maximum el estimate for the variance

        Parameters
        ----------

        lower: Lowest value of variance to be computed and plotted

        upper: Highest value of the variance to be computed and plotted

        step: Interval between each plot point.


        sig: Will draw a horizontal line at 1- sig. default | .05

        This function can be helpful when trying to determine limits
         in the ci_var function.

        """
        sig = 1 - sig
        p_vals = []
        for test in np.arange(lower, upper, step):
            p_vals.append(self.hy_test_var(test)[0])
        p_vals = np.asarray(p_vals)
        plt.plot(np.arange(lower, upper, step), p_vals)
        plt.plot(np.arange(lower, upper, step), (1 - sig) * \
                 np.ones(len(p_vals)))
        return  'Type plt.show to see the figure'

    def mv_hy_test_mean(self, mu_array, print_weights=False):

        """
        Returns the -2 * log likelihood and the p_value
        for a multivariate hypothesis test of the mean

        Parameters
        ----------
        mu_array : 1d array of hypothesized values for the mean

        Optional
        --------

        print_weights: If True, returns the weights that maximize the
            likelihood of mu_array default | False.

        """

        if len(mu_array) != self.endog.shape[1]:
            raise Exception('mu_array must have the same number of \
                           elements as the columns of the data.')
        mu_array = mu_array.reshape(1, self.endog[1])
        means = np.ones((self.endog.shape[0], self.endog.shape[1]))
        means = mu_array * means
        self.est_vect = self.endog - means
        start_vals = 1 / self.nobs * np.ones(self.endog.shape[1])
        eta_star = self.modif_newton(start_vals)
        denom = 1 + np.dot(eta_star, self.est_vect.T)
        self.new_weights = 1 / self.nobs * 1 / denom
        llr = np.sum(np.log(self.nobs * self.new_weights))
        p_val = 1 - chi2.cdf(-2 * llr, len(mu_array))
        if print_weights:
            return p_val, -2 * llr, self.new_weights
        else:
            return p_val, -2 * llr

    def mv_mean_contour(self, mu1_l, mu1_u, mu2_l, mu2_u, step1, step2,
                        levs=[.2, .1, .05, .01, .001], plot_dta=False):
        """

        Creates confidence region plot for the mean of bivariate data

        Parameters
        ----------

        m1_l: Minimum value of the mean for variable 1

        m1_u: Maximum value of the mean for variable 1

        mu2_l: Minimum value of the mean for variable 2

        mu2_u: Maximum value of the mean for variable 2

        step1: Increment of evaluations for variable 1

        step2: Increment of evaluations for variable 2


        Optional
        --------
        levs: Levels to be drawn on the contour plot.
        default | [.2, .1 .05, .01, .001]

        plot_dta: If True, makes a scatter plot of the data on
        top of the contour plot. defauls | False.

        Notes
        -----
        The smaller the step size, the more accurate the intervals
        will be.

        Example
        -------

        two_rvs = np.random.standard_normal((20,2))
        el_analysis = el.DescStat(two_rvs)
        contourp = el_analysis.mv_mean_contour(-2, 2, -2, 2, .1, .1)
        contourp
        >>>Type plt.show() to see plot
        plt.show()


        """

        if self.endog.shape[1] != 2:
            raise Exception('Data must contain exactly two variables')
        x = (np.arange(mu1_l, mu1_u, step1))
        y = (np.arange(mu2_l, mu2_u, step2))
        pairs = itertools.product(x, y)
        z = []
        for i in pairs:
            z.append(self.mv_hy_test_mean(np.asarray(i))[0])
        X, Y = np.meshgrid(x, y)
        z = np.asarray(z)
        z = z.reshape(X.shape[1], Y.shape[0])
        fig = plt.contour(x, y, z.T, levels=levs)
        plt.clabel(fig)
        if plot_dta:
            plt.plot(self.endog[:, 0], self.endog[:, 1], 'bo')
        return 'Type plt.show to see the figure'

    def mean_var_contour(self, mu_l, mu_h, var_l, var_h, mu_step,
                        var_step,
                        levs=[.2, .1, .05, .01, .001]):
        """

        Returns a plot of the confidence region for a univariate
        mean and variance.

        Parameters
        ----------

        mu_l: Lowest value of the mean to plot

        mu_h: Highest value of the mean to plot

        var_l: Lowest value of the variance to plot

        var_h: Highest value of the variance to plot

        mu_step: Increments to evaluate the mean

        var_step: Increments to evaluate the mean

        Optional
        --------

        At Which values of significance the contour lines will be drawn.
        default | [.2, .1, .05, .01, .001]

        """

        mu_vect = list(np.arange(mu_l, mu_h, mu_step))
        var_vect = list(np.arange(var_l, var_h, var_step))
        z = []
        for sig0 in var_vect:
            self.sig2_0 = sig0
            for mu0 in mu_vect:
                z.append(self.opt_var(mu0, pval=True))
        z = np.asarray(z).reshape(len(var_vect), len(mu_vect))
        fig = plt.contour(mu_vect, var_vect, z, levels=levs)
        plt.clabel(fig)
        return 'Type plt.show to see the figure'

    ## TODO: Use gradient and Hessian to optimize over nuisance params
    ## TODO: Use non-nested optimization to optimize over nuisance
    ## parameters.  See Owen pgs 234- 241

    def hy_test_skew(self, skew0, nuis0=None, mu_min=None,
                     mu_max=None, var_min=None, var_max=None,
                     print_weights=False):
        """

        Returns the p_value and -2 * log_likelihood for the hypothesized
        skewness.

        Parameters
        ----------
        skew0: Skewness value to be tested

        Optional
        --------

        mu_min, mu_max, var_min, var_max: Minimum and maximum values
        of the nuisance parameters to be optimized over.  If None,
        the function computes the 95% confidence interval for
        the mean and variance and uses the resulting values.

        print_weights: If True, function also returns the weights that
        maximize the likelihood ratio. default | False.

        """

        self.skew0 = skew0
        if nuis0 is not None:
            start_nuisance = nuis0
        else:
            start_nuisance = np.array([self.endog.mean(),
                                       self.endog.var()])
        if mu_min is not None:
            mu_lb = mu_min
        else:
            mu_lb = self.ci_mean()[0]

        if mu_max is not None:
            mu_ub = mu_max
        else:
            mu_ub = self.ci_mean()[1]

        if var_min is None or var_max is None:
            var_ci = self.ci_var()

        if var_min is not None:
            var_lb = var_min
        else:
            var_lb = var_ci[0]

        if var_max is not None:
            var_ub = var_max
        else:
            var_ub = var_ci[1]

        llr = optimize.fmin_l_bfgs_b(self.opt_skew, start_nuisance,
                                     approx_grad=1,
                                     bounds=[(mu_lb, mu_ub),
                                              (var_lb, var_ub)])[1]
        p_val = 1 - chi2.cdf(llr, 1)
        if print_weights:
            return p_val, llr, self.new_weights
        return p_val, llr

    def hy_test_kurt(self, kurt0, nuis0=None, mu_min=None,
                     mu_max=None, var_min=None, var_max=None,
                     print_weights=False):
        """

        Returns the p_value and -2 * log_likelihood for the hypothesized
        kurtosis.

        Parameters
        ----------
        kurt0: kurtosis value to be tested

        Optional
        --------

        mu_min, mu_max, var_min, var_max: Minimum and maximum values
        of the nuisance parameters to be optimized over.  If None,
        the function computes the 95% confidence interval for
        the mean and variance and uses the resulting values.

        print_weights: If True, function also returns the weights that
        maximize the likelihood ratio. default | False.

        """

        self.kurt0 = kurt0
        if nuis0 is not None:
            start_nuisance = nuis0
        else:
            start_nuisance = np.array([self.endog.mean(),
                                       self.endog.var()])
        if mu_min is not None:
            mu_lb = mu_min
        else:
            mu_lb = self.ci_mean()[0]

        if mu_max is not None:
            mu_ub = mu_max
        else:
            mu_ub = self.ci_mean()[1]

        if var_min is None or var_max is None:
            var_ci = self.ci_var()

        if var_min is not None:
            var_lb = var_min
        else:
            var_lb = var_ci[0]

        if var_max is not None:
            var_ub = var_max
        else:
            var_ub = var_ci[1]

        llr = optimize.fmin_l_bfgs_b(self.opt_kurt, start_nuisance,
                                     approx_grad=1,
                                     bounds=[(mu_lb, mu_ub),
                                              (var_lb, var_ub)])[1]
        p_val = 1 - chi2.cdf(llr, 1)
        if print_weights:
            return p_val, llr, self.new_weights
        return p_val, llr