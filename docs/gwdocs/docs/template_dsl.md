# Template DSL

[Snippets](snippets.md) are the most bare-bones way of generating code. A slightly nicer interface, [writers](writer.md), exist which helps writing lines and handling indentation.
However, in many cases, these approaches are too low-level and involved. If you have a 

you may actually prefer templates

## When to use ?
The chapter on writing [a template engine](http://aosabook.org/en/500L/a-template-engine.html) from the "500 lines or less" book makes an interesting observation. Programming languages excel when the content is mostly dynamic (e.g. meant to be evaluated), templates excel when the content is mostly static (literal) with bits of dynamic, executable content.

For those mostly dynamic scenarios, use the line-writer or write to the file directly. However, in situations where there is much more static than dynamic content, the template DSL may be the better choice.

## Introduction

The basic template DSL is very simple, it consists of:

* literals (text)
* expressions
* blocks
    * components

#### Literals
Literals are pieces of text which are written directly to the compiled file as-is. This is (often) the majority of the content in a template.

Example
```c
// Hello, world!
// some code:
int sum2(int a, int b) {
    return a + b;
}
```

In ghostwriter, all content in a template which doesn't explicitly escape the template-mode are treated as literal content and written out as-is to the file being compiled.

#### Expressions

The example below uses expressions to evaluate two variables, `var1` and `var2` and render the final template.
```c
int sum2(int <<var1>>, int <<var2>>) {
    return <<var1>> + <<var2>>;
}
```

If `var1` is `"first"` and `var2` is `"second"`, then the result would be:
```c
int sum2(int first, int second) {
    return first + second;
}
```

Note - expressions can take *any* Python expression you can think of, `var1.lower()` or `self.my_method(arg1, foo='val2')` are perfectly legal.

#### Blocks
Blocks allow you to extend the DSL as needed. The only requirements for blocks is that their name starts with a lowercase character and that they have an start- and an end line.

##### Using blocks

A block has a start and and end line, perhaps some argument(s) and a body:
```
% <block name> [<argument(s)>]
<body>
% /<block name>
```

In practice, this might look like so:

```
% if age >= 10
Santa is not real!
...
Hey, stop crying..!
% /if
```

or:

```
% for n in range(1, 4)
print("<<n>>...")
% /for
```

Note how the built-in `if`- and `for`-blocks both accept some argument, but that the syntax of this is completely different.
What a block does with its argument(s) and its body is entirely up to the block.


##### Summary
* blocks have a name, this must start with a lowercase character
* block arguments:
    * follow the block name on the start line
    * the format expected depends entirely on the type of block
* the block body:
    * the content between the block start- and end lines
    * may treat the content as DSL or something else (e.g. XML), it depends on the block's implementation
* built-in blocks
    * `if` - follows Python's syntax for if-blocks
    * `for` - follows Python's syntax for for-loops
* You can write your own blocks, if desired.

##### if-block
The `if`-block works *exactly* like a standard Python if:

```
% if self.platform() == 'linux'
print("linux is awesome!")
% /if
```

The if-block also supports `elif` for alternate clauses and `else`, just as a standard Python if-block would:

```
% if self.platform() == 'linux'
print("yay! penguins!")
% elif self.platform() == 'windows'
print("boo! windows!")
% else
print("what. are. you. running? O_O")
% /if
```

##### for-block
The `for`-block works *exactly* like a standard python for-loop:

```
% for number in range(3, 0, -1):
print("<<number>>...")
% /for
print("time's up!")
```

You can destructure the loop element as in regular Python:
```
% for x, y, rest in ml
<<x>>, <<y>> and <<rest>>
% /for
```
Given a list of tuples like so: `ml = [(1,3,5,7), (2,4,6,8)]`, the result would be:
```
1, 3 and [5, 7]
2, 4 and [6, 8]
```

#### Components
Components are a special kind of blocks which are implemented as a regular Python class. The way to tell apart components from blocks is that their name *must* start with a capital letter. Hence `foo` is a block and `Foo` is a component.

##### Using components
Using components uses the same syntax as using a block, e.g.:

```
% Acknowledgements ['peter', 'bertha', 'sally']
The following would never have been possible without the following people
% /Acknowledgements
```

However, arguments to the component are passed as arguments to the class' constructor, this means that:
```
% Acknowledgements ['peter', 'bertha', 'sally']
```
Is equivalent to the following Python:
```python
Acknowledgements(['peter', 'bertha', 'sally'])
```

Also, the body, the lines between `% Component ...` and `% /Component` are evaluated as DSL and is available to the component's template as the `body` variable.

##### Implementing components

```python
from ghostwriter.utils.template.dsl import Component

class Acknowledgements(Component):
    def __init__(self, people, prefix=)
    @property
    def template(self) -> str:
        return """\
        ---- Credits ----
        <<body>>:
        % for person in people:
        * <<person>>
        % /for
        """
```

##### Summary
* Components are implemented as a class in Python
* The name of the Component must start with an uppercase letter
* The arguments to a component use Python syntax for arguments to functions
* The body of the component is regular DSL which may use other components etc.
