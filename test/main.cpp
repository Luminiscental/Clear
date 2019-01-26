#include <iostream>
void print() {
    std::cout << std::endl;
}
template <typename T, typename ...Arguments>
void print(T first, Arguments... args) {
    std::cout << first;
    print(args...);
}
long factorial(const long n ){
if(n == 0){
return 1 ;
}
return n * factorial(n - 1) ;
}
long fibb(const long n ){
if(n == 1 || n == 2){
return 1 ;
}
else{
return fibb(n - 1) + fibb(n - 2) ;
}
}
double prod(const double a ,const double b ){
return a * b ;
}
int main(){
print("-- Hello World! --") ;
print() ;
print("11! = ", factorial(11), ", 18th fibb = ", fibb(18)) ;
print("3.14 * 2.72 = ", prod(3.14, 2.72)) ;
}
