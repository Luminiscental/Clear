
func factorial(val n: long): long {

    if (n == 0) {

        return 1
    }
    
    return n * factorial(n - 1)
}

func fibb(val n: long): long {

    if (n == 1 || n == 2) {

        return 1

    } else {

        return fibb(n - 1) + fibb(n - 2)
    }
}

func prod(val a: double, val b: double): double {

    return a * b
}

func main() {

    print("-- Hello World! --")
    print()
    print("11! = ", factorial(11), ", 18th fibb = ", fibb(18))
    print("3.14 * 2.72 = ", prod(3.14, 2.72))
}
