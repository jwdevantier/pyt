# Template DSL

While the raw [Snippets](snippets.md) interface is provided, it is primarily intended as an extension mechanism. The template DSL, which builds on top of the snippet abstraction, is intended as the primary way to implement code generation with Ghostwriter.

## When to use ?
The chapter on writing [a template engine](http://aosabook.org/en/500L/a-template-engine.html) from the "500 lines or less" book makes a good point. Programming languages excel when the content is mostly dynamic (e.g. meant to be evaluated), templates excel when the content is mostly static (literal) with bits of dynamic, executable content.

For those mostly dynamic scenarios, use the line-writer or write to the file directly. However, in situations where there is much more static than dynamic content, the template DSL may be the better choice.

## Introduction

The basic template DSL is very simple, it consists of:

* literals (text)
* expressions
* blocks

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

The example below uses expressions to evaluate two variables, `var1` and `var2` and render the final template:
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
% <block name>[<argument(s)>]
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
* blocks have a name (e.g. `for`, `if`, `r`)
* block arguments:
    * follow the block name on the start line
    * the format expected depends *entirely* on the type of block
* the block body:
    * the content between the block start- and end lines
* built-in blocks
    * `if` - follows Python's syntax for if-blocks
    * `for` - follows Python's syntax for for-loops
    * `r` - render a Component in place of the block

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
% for number in range(3, 0, -1)
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
Components are the building blocks of the DSL. Components allow you to reuse bits of DSL, by packaging it into a component. Components can take arguments and can use the full power of Python to process these before the DSL template they contain is parsed.

##### Defining a Component
Before this gets too abstract, consider the following example. Here, we define a component called `Struct` which, given a name and a map of fields, renders a struct in Go's syntax:

```python
# somefile.py

class Struct(Component):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields
    
    template = """\
        type <<self.name>> struct {
            % for name, typ in self.fields.items()
            <<name>> <<typ>>
            % /for
        }"""
```

##### Using a component from a snippet

Using the `snippet` decorator, we can write a snippet using the component:
```python
@snippet()
def person_struct():
    return Struct('Person', {'name': 'string', 'age': 'int'})

```

Notice how we create and return an *instance* of the component we wish to render in place of the snippet.

Inside our templated file, we would get the following result:
```go
// <@@ somefile.person_struct @@>
type Person struct {
    name string
    age int
}
// <@@ /somefile.person_struct @@>
```

##### Using a component from the DSL
Components are used (rendered) from the DSL by using the `r` (render) block. `r` expects some *expression* which evaluates to a component instance. This gives a lot of flexibility. Typically, you would create an instance of some Component class directly in scope of your Component, but you can also pass component classes, or even fully initialized instances, along for a component to render.

To show the syntax of using the `r`-block and how resolving components work out, see the following example:

```python
# some snippet module

# import the Template API
from ghostwriter.utils.template.dsl import *

# import some files containing other components
from othermodule import ComponentA
import othermodule

class HelloThing(Component):
    def __init__(self, thing):
        self.thing = thing

    template = """
    hello, <<self.thing>>!
    """

class MyComponent(Component):
    def __init__(self, component: Component, component_class: t.Type['Component']):
        self.component = component
        self.component_class = component_class

    template = """
    %% Components in the same module (file) are automatically available:
    % r HelloThing('world')
    % /r

    %% You can reference imported Components
    % r ComponentA('some arg', other='arg')
    % /r

    %% You can access components defined imported modules
    % r othermodule.ComponentA('some arg', other='arg')
    % /r

    %% You can pass component classes to a component to make them in scope:
    %% (What concrete component we render is now dependent on which argument we get)
    % r self.component_class('arg1', 'arg2')
    % /r

    %% Finally, you can also pass in a fully initialized component, this means the
    %% Using component (in this case, 'MyComponent') doesn't need to know which
    %% arguments to provide the component:
    % r self.component
    % /r
    """
```

##### Component bodies
Until now, all examples have opened and closed the render (`r`) block immediately. But whatever DSL code you write within the the block will be passed along to the component as a special `body` variable. You can use this to inject DSL code into some part of the component.

In the Component's DSL, simply insert the line `% body` whereever you would like the contents of the block's body to be inserted into the component's DSL template.
Below is an example

```python
# <snippet_dir>/email.py
class Email(Component):
    def __init__(self, recipient, sender):
        self.recipient = recipient
        self.sender = sender
        self.name = ' '.join([s.capitalize() for s in sender.split('@')[0].split('-')])

    template = """
    To: <<self.recipient>>
    From: <<self.sender>>

    % body

    Regards, <<self.name>>.
    EvilCorp - Eroding your privacy with 'free' services.

    This message is confidential and intended for the recipient specified
    in the message only. It is strictly forbidden to share any part of this
    message"""


class MyMessage(Component):
    template = """
    % r Email('joe@example.org', 'jane-doe@evilcorp.org')
    Dear Joe,
    
    We have a business proposal for you, please swing by our offices
    at your earliest convenience.
    % /r"""


@snippet
def my_message():
    return MyMessage()
```

```
//<@@email.my_message@@>
To: joe@example.org
From: jane-doe@evilcorp.org

Dear Joe,

We have a business proposal for you, please swing by our offices
at your earliest convenience.

Regards, Jane Doe.
EvilCorp - Eroding your privacy with 'free' services.

This message is confidential and intended for the recipient specified
in the message only. It is strictly forbidden to share any part of this
message
//<@@/email.my_message@@>
```

##### Summary
* A Component is implemented as a class in Python
* Components contain a template string, written in the DSL.
* Components can receive arguments which can alter the result of rendering the DSL
* Arguments are passed to the component's constructor - the full power of Python can be used to process the arguments
* Components have a scope containing:
    * all modules and components imported into the module (file) where the Component is defined
    * all other components defined in the same module
    * all variables and methods bound to the component, accessible via `self`, as in ordinary Python
* A component can receive a body, also written in the DSL, this is written between the opening and closing `r` tags
