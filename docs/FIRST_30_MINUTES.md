# Your First 30 Minutes with NexLang

No programming-language jargon required. Follow along in order.

## Minute 1 - Verify installation

Open a terminal and run:
```
nex --version
```
You should see `NexLang 0.3.0`. If not, go to
[USER_GUIDE.md, Section 1](USER_GUIDE.md#1-installation-guide) first, then
come back here.

## Minute 5 - Hello World

Create a file `hello.nex` containing:
```
SAY "Hello, World!"
```
Run:
```
nex hello.nex
```
You should see `Hello, World!` printed. `SAY` prints things to the screen.

## Minute 10 - Variables

Edit `hello.nex` (or make a new file) to try:
```
SET name TO "your name here"
SET age TO 25

SAY "Hi, {name}!"
SAY "You are {age} years old."

age = age + 1
SAY "Next year you'll be {age}."
```
Run it again. `SET ... TO ...` creates a variable; `=` changes an existing
one; `{ }` inside a string inserts a value.

## Minute 15 - Conditions

Add this:
```
IF age IS AT LEAST 18 THEN
    SAY "You can vote."
OTHERWISE
    SAY "Not old enough to vote yet."
END
```
`IF ... THEN ... OTHERWISE ... END` makes a decision. Try changing `age` to
see both branches run.

## Minute 20 - Loops

Add this:
```
SET count TO 1
WHILE count IS AT MOST 5
    SAY "Number: {count}"
    count = count + 1
END
```
This prints `Number: 1` through `Number: 5`. `WHILE` repeats its block as
long as the condition stays true.

## Minute 25 - A tiny function-like structure

NexLang doesn't have functions yet (planned - see
[ROADMAP.md](ROADMAP.md)), so instead, practice organizing repeated logic
with a loop and variables:
```
SET total TO 0
SET i TO 1
REPEAT 5 TIMES
    total = total + i
    i = i + 1
END
SAY "Sum of 1 through 5 is {total}"
```
Expected output: `Sum of 1 through 5 is 15`.

## Minute 30 - Build a tiny program

Put it all together - a simple "even or odd" checker:
```
SET number TO 7

IF number % 2 IS 0 THEN
    SAY "{number} is even."
OTHERWISE
    SAY "{number} is odd."
END
```
Run it, then change `number` and re-run to check different values.

## What now?

- Try the interactive REPL: `nex repl` (type `END` on its own line to run what you've written)
- Try the graphical IDE: `nex` (see USER_GUIDE.md Section 10)
- Read the full [USER_GUIDE.md](USER_GUIDE.md) for every implemented
  feature and a 14-lesson course
- Browse [examples/](../examples) for more complete programs
- Check [ROADMAP.md](ROADMAP.md) to see what's coming (functions, lists,
  classes, files, and more)
