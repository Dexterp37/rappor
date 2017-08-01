import sys
from math import log

def p_star(f, p, q):
    return (f / 2.) * (p + q) + (1 - f) * p

def q_star(f, p, q):
    return (f / 2.) * (p + q) + (1 - f) * q 

def inner_factor(p_star, q_star):
    return (q_star * (1. - p_star)) / (p_star * (1. - q_star ))

def epsilon(h, inner):
    return h * log(inner)

def main(args):
    f = float(args[1])
    p = float(args[2])
    q = float(args[3])
    h = int(args[4])

    p_s = p_star(f, p, q)
    q_s = q_star(f, p, q)
    inner = inner_factor(p_s, q_s)
    e = epsilon(h, inner)
    print "{} ln({}) = {}".format(h, inner, e) 

if __name__ == "__main__":
    main(sys.argv)
