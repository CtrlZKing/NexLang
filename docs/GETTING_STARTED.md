# Getting Started with NexLang

This is a short, friendly on-ramp. For full installation details see
[USER_GUIDE.md](USER_GUIDE.md#1-installation-guide); for the exhaustive
manual see [USER_GUIDE.md](USER_GUIDE.md) itself.

## 1. Install (short version)

```bash
git clone <this-repo-url> nexlang
cd nexlang
pip install -e .
nex --version   # -> NexLang 0.3.0
```

## 2. Write and run your first program

Create `hello.nex`:
```
SAY "Hello, World!"
```
Run it:
```bash
nex hello.nex
```
You should see:
```
Hello, World!
```

## 3. Variables and arithmetic

```
SET price TO 19.99
SET quantity TO 3
SET total TO price * quantity
SAY "Total: {total}"
```

## 4. Making decisions

```
SET temperature TO 15

IF temperature IS ABOVE 25 THEN
    SAY "It's hot."
ELSE IF temperature IS ABOVE 10 THEN
    SAY "It's mild."
OTHERWISE
    SAY "It's cold."
END
```

## 5. Repeating things

```
SET count TO 1
WHILE count IS AT MOST 5
    SAY "Count: {count}"
    count = count + 1
END
```

## 6. Try the REPL

```bash
nex repl
```

Type a line, press Enter, and keep typing - nothing runs until you type a
line that's just `END`:

```
> SET x TO 10
> SAY x * x
> END
100
```

See [docs/USER_GUIDE.md, Section 9](USER_GUIDE.md#9-repl-guide) for why it
works this way and how blocks (`IF`/`WHILE`/`REPEAT`) behave there.

## 7. Try the graphical IDE

```bash
nex
```

Opens the NexLang IDE in its own window: a code editor with syntax
highlighting and smart indentation, an Output panel, and a Run button.
See [docs/USER_GUIDE.md, Section 10](USER_GUIDE.md#10-nexlang-ide-guide).

## 8. Where to go next

- [docs/FIRST_30_MINUTES.md](FIRST_30_MINUTES.md) - a structured 30-minute walkthrough
- [docs/USER_GUIDE.md](USER_GUIDE.md) - the full manual, including a 14-lesson course
- [docs/LANGUAGE.md](LANGUAGE.md) - complete reference of everything implemented
- [docs/CHEATSHEET.md](CHEATSHEET.md) - one-page syntax summary
- [examples/](../examples) - runnable example programs
- [docs/ROADMAP.md](ROADMAP.md) - what's coming next (functions, lists, classes, ...)
