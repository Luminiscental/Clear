syn keyword clrKeywords val var print if else and or return func while struct void this nil with as prop
hi link clrKeywords Type

syn keyword clrBuiltins str num int bool clock
hi link clrBuiltins PreProc

syn keyword clrBoolean true false
hi link clrBoolean Constant

syn match clrIdent '[a-zA-Z_][a-zA-Z0-9_]*'
hi link clrIdent Normal

syn match clrFunction '\(func\_s\+\)\@<=\([a-zA-Z_][a-zA-Z0-9_]*\)'
hi link clrFunction Function

syn match clrStruct '\(struct\_s\+\)\@<=\([a-zA-Z_][a-zA-Z0-9_]*\)'
hi link clrStruct Identifier

syn match clrProp '\(prop\_s\+\)\@<=\([a-zA-Z_][a-zA-Z0-9_]*\)'
hi link clrProp Identifier

syn match clrDecorator '@'
hi link clrDecorator Define

syn match clrNumber '\d\+\(\.\d\+\)\?'
hi link clrNumber Constant

syn match clrInteger '\d\+i'
hi link clrInteger Constant

syn match clrSymbol '[?\.,<>{}()!+=\*\-;:/]'
hi link clrSymbol Normal

syn region clrString start="\"" end="\""
hi link clrString String

syn region clrComment start="//" end="\n"
hi link clrComment Comment

