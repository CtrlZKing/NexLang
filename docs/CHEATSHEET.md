# NexLang Cheat Sheet (Phase 1 + 2 + 3 + 3b)

## Variables
```
SET x TO 10
SET name TO "Aditya"
SET active TO TRUE
x = 20                       # reassign (x must already exist)
SET a, b TO 1, 2             # multiple assignment
SET a, b TO b, a              # swap
```

## Output / Input
```
SAY "Hello!"
SAY "Hello {name}"           # interpolation, any expression inside { }
ASK "Your name?" INTO name    # reads TEXT input
```

## Operators
```
+  -  *  /  //  %  **                     arithmetic
==  !=  <  >  <=  >=                       comparison
IS  IS NOT  IS AT LEAST  IS AT MOST        readable comparison
IS ABOVE  IS BELOW  IS BETWEEN a AND b
IS EMPTY  IS NULL
CONTAINS  STARTS WITH  ENDS WITH           text / collection checks
AND  OR  NOT                               logical
+=  -=  *=  /=  //=  %=                    compound assignment
INCREASE x BY n   DECREASE x BY n          readable compound assignment
SIZE OF x                                   length of LIST/TEXT/MAP/SET
```

## Collections
```
SET numbers TO [5, 2, 9, 1]
ADD 10 TO numbers
REMOVE 2 FROM numbers
SAY numbers[0]              # indexing (negative counts from the end)
SAY numbers[1:3]            # slicing: [start:end], either bound optional
SAY SIZE OF numbers
SAY SUM(numbers)  AVERAGE(numbers)  MAXIMUM(numbers)  MINIMUM(numbers)
SAY SORTED(numbers)  REVERSED(numbers)  UNIQUE(numbers)  COUNT(numbers)

SET person TO {"name": "Aditya", "age": 15}     # map
SAY person["name"]
FOR EACH key, value IN person
    SAY "{key}: {value}"
END
SAY KEYS(person)  VALUES(person)

SET s TO SET_OF([1, 2, 2, 3])                   # set (no duplicates)
SET t TO TUPLE_OF([1, 2, 3])                    # tuple (immutable)
SAY LIST_OF(s)                                   # convert set/tuple back to a list
```

## Functions
```
FUNCTION greet(name = "friend")
    RETURN "Hello, " + name
END
SAY greet("Aditya")
SAY greet()

FUNCTION combine(a AS NUMBER, b AS NUMBER) RETURNS NUMBER   # typed
    RETURN a + b
END
```
Supports default params, recursion, local scope, and closures.

## Type annotations (checked by `nex check`, not enforced by `nex run`)
```
SET age AS NUMBER TO 15
SET nickname AS TEXT OR NOTHING TO NULL     # union = "optional"

FUNCTION f(x AS NUMBER) RETURNS TEXT
    RETURN "{x}"
END
```
Types: `NUMBER TEXT BOOLEAN NOTHING LIST MAP SET TUPLE FUNCTION ERROR ANY`

## Errors
```
TRY
    SAY 1 / 0
CATCH err
    SAY "Caught: {err}"
FINALLY
    SAY "always runs"
END
```

## Modules & Files
```
IMPORT "helpers.nex"

WRITE "text" TO FILE "notes.txt"
APPEND "more" TO FILE "notes.txt"
SET content TO READ FILE "notes.txt"
IF FILE "notes.txt" EXISTS THEN ... END
DELETE FILE "notes.txt"
```

## Standard-library functions
```
UPPERCASE(t)  LOWERCASE(t)  TRIM(t)  SPLIT(t, sep)  JOIN(list, sep)
REPLACE(t, old, new)  ROUND(n)  ROUND(n, digits)
RANDOM_BETWEEN(low, high)  CURRENT_TIME()  CURRENT_DATE()  WAIT(seconds)
```

## Conditionals
```
IF x IS AT LEAST 10 THEN
    SAY "big"
ELSE IF x IS AT LEAST 5 THEN
    SAY "medium"
OTHERWISE
    SAY "small"
END
```

## Loops
```
REPEAT 10 TIMES
    SAY "hi"
END

WHILE x IS BELOW 10
    x = x + 1
END

REPEAT UNTIL x IS 0
    x = x - 1
END

FOR EACH item IN numbers
    SAY item
END

FOR i FROM 1 TO 5
    SAY i
END

FOR i FROM 5 DOWN TO 1
    SAY i
END

BREAK        # exit loop early
CONTINUE     # skip to next iteration
```

## Comments
```
# a single-line comment
```

## Types (Phase 1 + 2 + 3)
```
NUMBER    10, 3.14, -2
TEXT      "hello"
BOOLEAN   TRUE, FALSE
NOTHING   NOTHING, NULL
LIST      [1, 2, 3]
MAP       {"a": 1}
SET       SET_OF([1, 2])
TUPLE     TUPLE_OF([1, 2])
FUNCTION  a declared FUNCTION
ERROR     what CATCH binds
```

## CLI
```
nex run file.nex     nex file.nex     nex check file.nex
nex repl             nex             nex ide
nex version          nex help [topic]
```
`nex repl` = terminal interactive mode (type `END` to run what you typed).
`nex` / `nex ide` = opens the graphical NexLang IDE.
`nex check` = syntax AND semantic checking (undefined names, type
mismatches, unreachable code) - see docs/USER_GUIDE.md Section 26.

---
Not yet available (see docs/ROADMAP.md): comprehensions, a `{1,2,3}` set
literal, classes, enums, pattern matching, lambdas/keyword args, package
manager, formatter, linter, debugger, LSP/VS Code extension.
