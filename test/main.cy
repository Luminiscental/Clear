
func factorial(val n: long): long {

    if (n == 0) {

        return 1
    }
    
    return n * factorial(n - 1)
}

func fibb(val n: long): long {

    if (n == 1 || n == 2) {

        return 1
    }

    return fibb(n - 1) + fibb(n - 2)
}

func main() {

    print("-- Hello World! --")
    print()
    print("11! = ", factorial(11), ", 18th fibb = ", fibb(18))
}
