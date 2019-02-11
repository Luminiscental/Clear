
func factorial(val n: Int): Int {

    if (n == 0) {

        1

    } else {

        n * factorial(n - 1)
    }
}

func main() {

    print("Hello World!")
}
