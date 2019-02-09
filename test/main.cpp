#include <iostream>
void print() {
    std::cout << std::endl;
}
template <typename T, typename ...Arguments>
void print(T first, Arguments... args) {
    std::cout << first;
    print(args...);
}
{function: factorial(variable: n, type: long)longFunction body
{    if 
(n == 0
)
 
{    
}
    return n * factorial
(n - 1
)

}
function: fibb(variable: n, type: long)longFunction body
{    if 
(n == 1 || n == 2
)
 
{    
}
 else 
{        return fibb
(n - 1
)
 + fibb
(n - 2
)
    
}

}
function: defaulting(variable: x, type: double, value: Expression)voidFunction body
{    print
("defaulting: 
{ x = ", x, " 
}
"
)

}
function: main()voidFunction body
{    print
("-- Hello World! --"
)
    print
(
)
    print
("11! = ", factorial
(11
)
, ", 18th fibb = ", fibb
(18
)

)
    print
("x = ", x
)
    defaulting
(
)
    defaulting
(3.1415926536
)

}
}