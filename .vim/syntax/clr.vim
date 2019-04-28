
" Clear language syntax
syn keyword clrKeywords val var print if else and or return func while struct void this nil
hi link clrKeywords Type

syn keyword clrBuiltins str num int bool clock
hi link clrBuiltins Function

syn match clrDecorator '@'
hi link clrDecorator Define

syn match clrIdent '[a-zA-Z_][a-zA-Z0-9_]*'
hi link clrIdent Normal

syn match clrNumber '\d\+\(\.\d\+\)\?'
hi link clrNumber Constant

syn match clrInteger '\d\+i'
hi link clrInteger Constant

syn match clrBoolean 'true\|false'
hi link clrBoolean Constant

syn region clrString start="\"" end="\""
hi link clrString String

syn match clrComment '//.*'
hi link clrComment Comment

syn match clrSymbol '[?\.,<>{}()!+=\*\-;:/]\(/\)\@!'
hi link clrSymbol Normal

