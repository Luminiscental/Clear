
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

func defaulting(val x: double = 3.14) {

    print("defaulting: { x = ", x, " }")
}

func main() {

    print("-- Hello World! --")
    print()
    print("11! = ", factorial(11), ", 18th fibb = ", fibb(18))

    val x = 3
    print("x = ", x)

    defaulting()
    defaulting(3.1415926536)
}
