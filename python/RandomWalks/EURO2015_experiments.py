#!/usr/bin/env python


"""

James McDermott [jmmcd@jmmcd.net]

This script runs the simple experiments required for the EURO 2015
paper "Measuring exploration-exploitation behaviour of neighbourhood
operators in permutation search spaces".

If something doesn't work, please email me [jmmcd@jmmcd.net] and I
will help.
"""


import numpy as np
import scipy.stats
import random
import sys
import os
import os.path
import itertools
from collections import OrderedDict
import matplotlib.pyplot as plt
import cPickle as pickle

import random_walks
import plotting


setups = [
    # representation, operator
    ("ga_length_8", "per_gene"),
    ("ga_length_10", "per_gene"),
    ("ga_length_12", "per_gene"),
    ("ga_length_8", "per_ind"),
    ("ga_length_10", "per_ind"),
    ("ga_length_12", "per_ind"),
    ("depth_1", "subtree"),
    ("depth_2", "subtree"),
    ("tsp_length_6", "2opt"),
    ("tsp_length_7", "2opt"),
    ("tsp_length_8", "2opt"),
    ("tsp_length_6", "3opt"),
    ("tsp_length_7", "3opt"),
    ("tsp_length_8", "3opt"),
    ("tsp_length_6", "swap"),
    ("tsp_length_7", "swap"),
    ("tsp_length_8", "swap"),
    ]

def mu_GINI(path_results):
    pmuts = [0.0001, 0.001/3, 0.001, 0.01/3, 0.01, 0.1/3, 0.1, 1.0/3]    
    prop_unique_rw_results = {}
    mu_GINI_tp_results = {}
    mu_GINI_mfpt_results = {}

    print "Representation size mu(GINI(tp)) sigma(GINI(tp)) mu(GINI(mfpt)) sigma(GINI(mfpt))"
    for rep, op in setups:

        # first get the TP and MFPT matrices, may already be on disk
        n = int(rep.split("_")[-1])
        dirname = os.path.join(path_results, rep + "_" + operator)
        tp_path = os.path.join(dirname, "TP.dat")
        mfpt_path = os.path.join(dirname, "MFPT.dat")
        try:
            tp = np.genfromtxt(tp_path)
            mfpt = np.genfromtxt(mfpt_path)
        except:
            if "ga" in rep:
                tp, _ = random_walks.generate_ga_tm(ga_length, pmut=1.0/n)
                np.savetxt(tp_path, tp)
                random_walks.read_and_get_dtp_mfpt_sp_steps(dirname)
            elif "depth" in rep:
                pass # already generated by Java code
            elif "tsp" in rep:
                tp = random_walks.sample_transitions(length, move)
                np.savetxt(tp_path, tp)
                random_walks.read_and_get_dtp_mfpt_sp_steps(dirname)

        # get mu_GINI and stddev_GINI
        mu_GINI_tp, sigma_GINI_tp = mu_sigma_GINI(TP)
        mu_GINI_mfpt, sigma_GINI_mfpt = mu_sigma_GINI(MFPT)

        mu_GINI_tp_results[rep, op] = mu_GINI_tp
        mu_GINI_mfpt_results[rep, op] = mu_GINI_mfpt
        
        print "%s %s mu(GINI(tp)): %.3f %.3f %.3f %.3f" % (rep, op, mu_GINI_tp, sigma_GINI_tp, mu_GINI_mfpt, sigma_GINI_mfpt)

        # use a rw of length equal to size of space
        # expect many duplicates even with explorative operators
        # but many more with exploitative ones
        prop_unique_rw_results[rep, op] = [rw_experiment(tp, len(tp))
                                           for i in range(30)]

    plot_prop_unique_rw(path_results, prop_unique_rw_results, mu_GINI_tp_results, mu_GINI_mfpt_results)

def plot_prop_unique_rw(path_results, results, mu_GINI_tp, mu_GINI_mfpt):

    # do the TP one
    x = [mu_GINI_tp[rep, op] for rep, op in setups]
    y_mean = [np.mean(results[rep, op] for rep, op in setups)]
    y_err = [np.std(results[rep, op] for rep, op in setups)]

    # transpose, sort, transpose
    xyz = [x, y_mean, y_err]
    xyz = zip(*xyz)
    xyz.sort()
    x, y_mean, y_err = xyz
    plt.figure(figsize=(5, 2.5))
    plt.errorbar(x, y, yerr=y_err, lw=3)
    plt.title("")
    plt.xlabel(r"$\mu(\text{GINI}(p))$", fontsize=16)
    plt.ylabel("Unique\nindividuals")
    plt.ylim(0, 1)
    filename = os.path.join(path_results, "_prop_unique_rw_tp")
    plt.savefig(filename + ".pdf")
    plt.savefig(filename + ".eps")
    plt.close()
        
    # do the MFPT one
    x = [mu_GINI_mfpt[rep, op] for rep, op in setups]
    y_mean = [np.mean(results[rep, op] for rep, op in setups)]
    y_err = [np.std(results[rep, op] for rep, op in setups)]
    
    # transpose, sort, transpose
    xyz = [x, y_mean, y_err]
    xyz = zip(*xyz)
    xyz.sort()
    x, y_mean, y_err = xyz
    plt.figure(figsize=(5, 2.5))
    plt.errorbar(x, y, yerr=y_err, lw=3)
    plt.title("")
    plt.xlabel(r"$\mu(\text{GINI}(t))$", fontsize=16)
    plt.ylabel("Unique\nindividuals")
    plt.ylim(0, 1)
    filename = os.path.join(path_results, "_prop_unique_rw_tp")
    plt.savefig(filename + ".pdf")
    plt.savefig(filename + ".eps")
    plt.close()

            

def ga_hc_experiment(path_results):
    """Run some hill-climbs in a bitstring space with different
    per-gene mutation values."""
    pmuts = [0.0001, 0.001/3, 0.001, 0.01/3, 0.01, 0.1/3, 0.1, 1.0/3]    
    noise_vals = [0, 1, 10, 100, 1000]
    results = OrderedDict()

    fit_path = os.path.join(path_results, "ga_length_10", "fitness_vals.dat")
    try:
        ga_fit = np.genfromtxt(fit_path)
    except:
        ga_fit = random_walks.onemax_fitvals(ga_length)
        np.savetxt(fit_path, ga_fit)

    mu_GINI_vals = {}
        
    for pmut in pmuts:
        ga_length = 10
        tp_path = os.path.join(path_results, "ga_length_10_per_gene_%.6d" % pmut, "TP.dat")
        
        try:
            ga_tp = np.genfromtxt(tp_path)
        except:
            ga_tp, _ = random_walks.generate_ga_tm(ga_length, pmut=pmut)
            np.savetxt(tp_path, ga_tp)

        # just get mu(GINI()), don't bother with sigma(GINI())
        mu_GINI_vals[pmut] = random_walks.mean_gini_coeff(ga_tp)

        reps = 30
        steps = 50
        for rep_name, tp, fitvals in [["ga", ga_tp, ga_fit]]:

            for noise_val in noise_vals:

                tmp_fit = random_walks.permute_vals(fitvals, noise_val)

                for rep in range(reps):
                    tp_tmp = random_walks.uniformify(tp, uniformify_val)
                    samples, fit_samples, best = random_walks.hillclimb(tp_tmp, tmp_fit,
                                                                        steps, rw=False)
                    x = best
                    results[rep_name, pmut, noise_val, rep] = x
    return results, mu_GINI_vals

def plot_ga_hc_results(results, mu_GINI_vals, path_results):
    """Plot the results of the GA HC experiments above."""
    pmuts = [0.0001, 0.000333, 0.001, 0.00333, 0.01, 0.0333, 0.1, 0.333]
    noise_vals = [0, 1, 10, 100, 1000]

    reps = 30
    for rep_name in ["ga"]:
        for noise_val in noise_vals:
            mu = []
            err = []

            for pmut in pmuts:
                x = [results[rep_name, pmut, noise_val, rep]
                     for rep in range(reps)]
                mu.append(np.mean(x))
                err.append(np.std(x))

            plt.figure(figsize=(5, 2.5))
            plt.errorbar(mu_sigma_vals, mu, yerr=err, lw=3)
            plt.title(rep_name.upper() + r" OneMax with noise %d" % noise_val)
            plt.xlabel(r"$\mu(\text{GINI}(p))$", fontsize=16)
            plt.ylabel("Fitness")
            plt.ylim(0, 10)
            filename = os.path.join(path_results, rep_name + "_noise_%d_hc" % noise_val)
            plt.savefig(filename + ".pdf")
            plt.savefig(filename + ".eps")

def write_ga_fitness_vals(n):
    ga_fit = onemax_fitvals(n)
    ga_outfile = open(dirname + "/ga_length_" + str(n) + "/fitness_vals.dat", "w")
    for fitval in ga_fit:
        ga_outfile.write(fitval)

def write_gp_trees(path_results):
    n = 2
    import generate_trees
    outfile = file(os.path.join(path_results, "depth_2", "all_trees.dat"), "w")
    trees_depths = generate_trees.trees_of_depth_LE(n,
                                                    ("x0", "x1"),
                                                    OrderedDict([("*", 2), ("+", 2),
                                                                 ("-", 2), ("AQ", 2)]),
                                                    as_string=False)
    for tree, depth in trees_depths:
        # hack hack: this is because a single variable gets a bare x0 instead of 'x0'.
        if len(tree) < 3:
            tree = '"%s"' % tree

        outfile.write(str(tree) + "\n")

def operator_difference_experiment():
    opss = ("2opt", "3opt", "3opt_broad", "swap")
    for ops in itertools.combinations(opss, 2):
        basedir = "/Users/jmmcd/Dropbox/GPDistance/results/tsp_length_6_"
        ps = [np.genfromtxt(basedir + op + "/TP.dat") for op in ops]
        names = "+".join(ops)
        delta = random_walks.operator_difference_RMSE(*ps)
        print names, delta
        
def combinations_var_len(x):
    """Combinations of all lengths: 'ABC' -> '', 'A', 'B', 'C', 'AB', 'AC', 'BC', 'ABC'"""
    for i in range(len(x) + 1):
        for item in itertools.combinations(x, i):
            yield item
        
def compound_operators_experiment():
    print "Operator(s) mu(GINI(tp)) sigma(GINI(tp)) mu(GINI(mfpt)) sigma(GINI(mfpt))"
    opss = ("2opt", "3opt", "3opt_broad", "swap")
    for ops in combinations_var_len(opss)[1:]: # don't need empty one
        basedir = "/Users/jmmcd/Dropbox/GPDistance/results/tsp_length_6_"
        ps = [np.genfromtxt(basedir + op + "/TP.dat") for op in ops]
        names = "+".join(ops)
        wts = [1.0 / len(ops) for _ in ops]
        compound_tp = random_walks.compound_operator(wts, ps)
        compound_mfpt = random_walks.get_mfpt(compound_tp)
        
        mu_GINI_tp, sigma_GINI_tp = random_walks.mu_sigma_GINI(compound_tp)
        mu_GINI_mfpt, sigma_GINI_mfpt = random_walks.mu_sigma_GINI(compound_mfpt)

        print "%s mu(GINI(tp)): %.3f %.3f %.3f %.3f" % (names, mu_GINI_tp, sigma_GINI_tp, mu_GINI_mfpt, sigma_GINI_mfpt)

            
def rw_experiment(tp):
    """Proportion of unique individuals in a random walk"""
    reps = 30
    results = []
    for rep in range(reps):
        samples = random_walks.random_walk(tp, steps)
        x = float(len(set(samples))) / len(samples)
        results.append(x)
    return results




def main():

    path_PODI_gp = "/Users/jmmcd/Documents/vc/PODI/src/gp.py"
    path_results = "/Users/jmmcd/tmp/results/"

    # make results dir
    try:
        os.makedirs(os.path.join(path_results, "depth_2"))
    except OSError:
        pass
    try:
        os.makedirs(os.path.join(path_results, "ga_length_10"))
    except OSError:
        pass

    # compile and run the Java code for generating transition matrix
    cwd = os.getcwd()
    os.chdir("../../java")
    cmd = "make all"
    os.system(cmd)
    cmd = "make completeMatricesDepth2"
    os.system(cmd)
    os.chdir(cwd)

    # generate all GP trees
    write_gp_trees(path_results)

    # use PODI's GP-fitness code to evaluate fitness of all GP trees
    cwd = os.getcwd()
    os.chdir(os.path.dirname(path_PODI_gp))
    sys.path.append(os.getcwd())
    import gp
    gp.read_trees_write_fitness_EuroGP2014(os.path.join(path_results, "depth_2", "all_trees.dat"),
                                           os.path.join(path_results, "depth_2", "all_fitness_values.dat"))
    os.chdir(cwd)

    results_file = os.path.join(path_results, "EuroGP_2014_results.pkl")
    try:
        # restore from a save, if it's been saved
        results = pickle.load(file(results_file))
        (ga_hc_results, ga_gp_rw_results, ga_fit, gp_fit, mu_sigma_vals) = results
    except:
        # run and save results
        ga_hc_results, mu_sigma_vals = ga_hc_experiment(path_results)
        ga_gp_rw_results, ga_fit, gp_fit = ga_gp_rw_experiment(path_results)
        results = (ga_hc_results, ga_gp_rw_results, ga_fit, gp_fit, mu_sigma_vals)
        pickle.dump(results, file(results_file, "w"))

    # plot
    plot_ga_hc_results(ga_hc_results, mu_sigma_vals, path_results)
    plot_ga_gp_rw_results(ga_gp_rw_results, mu_sigma_vals, path_results)


    # the stationary state and in-degree
    plotting.write_steady_state(os.path.join(path_results, "depth_2"))

if __name__ == "__main__":
    # compound_operators_experiment()
    operator_difference_experiment()
