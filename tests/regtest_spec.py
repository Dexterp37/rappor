#!/usr/bin/python
"""Print a test spec on stdout.

Each line has parameters for a test case.  The regtest.sh shell script reads
these lines and runs parallel processes.

We use Python data structures so the test cases are easier to read and edit.
"""

import optparse
import sys

#
# TEST CONFIGURATION
#

DEMO = (
    # (case_name distr num_unique_values num_clients values_per_client)
    # (num_bits num_hashes num_cohorts)
    # (p q f) (num_additional regexp_to_remove)
    ('demo1 gauss   100 100000 1', '32 1 64', '0.25 0.75 0.5', '0 NONE'),
    ('demo2 gauss   100 1000 1', '32 1 64', '0.25 0.75 0.5', '0 NONE'),
    ('demo3 gauss   100 10000 1', '32 1 64', '0.25 0.75 0.5', '0 NONE'),
    ('demo4 zipf1   100 100000 10', '32 1 64', '0.25 0.75 0.5', '100 v[0-9]*9$'),
    ('demo5 zipf1.5 100 100000 10', '32 1 64', '0.25 0.75 0.5', '100 v[0-9]*9$'),
)

DISTRIBUTIONS = (
    'unif',
    'exp',
    'gauss',
    'zipf1',
    'zipf1.5',
)

DISTRIBUTION_PARAMS = (
    # name, num unique values, num clients, values per client
    ('tiny', 100, 1000, 1),  # test for insufficient data
    ('small', 100, 1000000, 1),
    ('medium', 1000, 10000000, 1),
    ('large', 10000, 100000000, 1),
    # Params for testing how varying the number of clients affects the results
    ('clients1', 100, 10000000, 1),
    ('clients2', 100, 1000000, 1),
    ('clients3', 100, 500000, 1),
    ('clients4', 100, 100000, 1),
    ('clients5', 100, 50000, 1),
    ('clients6', 100, 25000, 1),
    # Params for testing the number of unique values
    ('unique1', 10, 1000000, 1),
    ('unique2', 100, 1000000, 1),
    ('unique3', 1000, 1000000, 1),
    # ...


)

# 'k, h, m' as in params file.
BLOOMFILTER_PARAMS = {
    '8x16x2': (8, 2, 16),  # 16 cohorts, 8 bits each, 2 bits set in each
    '8x32x2': (8, 2, 32),  # 32 cohorts, 8 bits each, 2 bits set in each
    '8x128x2': (8, 2, 128),  # 128 cohorts, 8 bits each, 2 bits set in each
    '128x8x2': (128, 2, 8),  # 8 cohorts, 128 bits each, 2 bits set in each

    # params for testing the size of the bloom filter
    '8x128x1' : (8, 1, 128),
    '8x128x2' : (8, 2, 128),
    '8x128x4' : (8, 4, 128),
    '8x128x8' : (8, 8, 128),

    # params for testing the number of hash functions

    # params for testing the number of cohorts
    '128x16x2': (128, 2, 8),  # 8 cohorts, 128 bits each, 2 bits set in each
    '128x32x2': (128, 2, 8),  # 8 cohorts, 128 bits each, 2 bits set in each
    '128x64x2': (128, 2, 8),  # 8 cohorts, 128 bits each, 2 bits set in each
    '128x128x2': (128, 2, 8),  # 8 cohorts, 128 bits each, 2 bits set in each

}

# 'p, q, f' as in params file.
PRIVACY_PARAMS = {
    'params1': (0.39, 0.61, 0.45),  # eps_1 = 1, eps_inf = 5:
    'params2': (0.225, 0.775, 0.0),  # eps_1 = 5, no eps_inf
    'params3': (0.75, 0.5, 0.75), 

}

# For deriving candidates from true inputs.
MAP_REGEX_MISSING = {
    'sharp': 'NONE',  # Categorical data
    '10%': 'v[0-9]*9$',  # missing every 10th string
}

# test configuration ->
#   (name modifier, Bloom filter, privacy params, fraction of extra,
#    regex missing)
TEST_CONFIGS = [
    ('typical', '8x128x2', 'params1', .2, '10%'),
    ('sharp', '8x128x2', 'params1', .0, 'sharp'),  # no extra candidates
    ('loose', '8x128x2', 'params2', .2, '10%'),  # loose privacy
    ('over_x2', '8x128x2', 'params1', 2.0, '10%'),  # overshoot by x2
    ('over_x10', '8x128x2', 'params1', 10.0, '10%'),  # overshoot by x10
    ('sharp2', '8x128x2', 'params3', .0, 'sharp'),

    # configuration for testing the bloom filter size
    ('sim_bloom_filter1', '8x128x2', 'params3', .0, 'sharp'),
    ('sim_bloom_filter2', '8x128x2', 'params3', .0, 'sharp'),
    # ...

    # configuration for testing the number of hash functions
    ('sim_hash1', '8x128x1', 'params3', .0, 'sharp'),
    ('sim_hash2', '8x128x2', 'params3', .0, 'sharp'),
    ('sim_hash3', '8x128x4', 'params3', .0, 'sharp'),
    ('sim_hash4', '8x128x8', 'params3', .0, 'sharp'),
    # ...

    # configuration for testing the number of cohorts
    ('sim_cohort1', '128x8x2', 'params3', .0, 'sharp'),
    ('sim_cohort2', '128x16x2', 'params3', .0, 'sharp'),
    ('sim_cohort3', '128x32x2', 'params3', .0, 'sharp'),
    ('sim_cohort4', '128x64x2', 'params3', .0, 'sharp'),
    ('sim_cohort5', '128x128x2', 'params3', .0, 'sharp'),


    # ...

    # configuration for testing different probabilities p, q, f
    ('sim_probs1', '8x128x2', 'params1', .0, 'sharp'),
    ('sim_probs2', '8x128x2', 'params2', .0, 'sharp'),
    ('sim_probs3', '8x128x2', 'params3', .0, 'sharp'),
    # ...


]

#
# END TEST CONFIGURATION
#


def main(argv):
  rows = []

  test_case = []
  for (distr_params, num_values, num_clients,
       num_reports_per_client) in DISTRIBUTION_PARAMS:
    for distribution in DISTRIBUTIONS:
      for (config_name, bloom_name, privacy_params, fr_extra,
           regex_missing) in TEST_CONFIGS:
        test_name = 'r-{}-{}-{}'.format(distribution, distr_params,
                                        config_name)

        params = (BLOOMFILTER_PARAMS[bloom_name]
                  + PRIVACY_PARAMS[privacy_params]
                  + tuple([int(num_values * fr_extra)])
                  + tuple([MAP_REGEX_MISSING[regex_missing]]))

        test_case = (test_name, distribution, num_values, num_clients,
                     num_reports_per_client) + params
        row_str = [str(element) for element in test_case]
        rows.append(row_str)

  for params in DEMO:
    rows.append(params)

  for row in rows:
    print ' '.join(row)

if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError, e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
