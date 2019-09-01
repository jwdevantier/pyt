# Design choices

When writing a code generator, there are many possible tradeoffs to make. This page describes those decisions made and why.

## Principles
### Prefer a general-purpose language to a DSL

Ghostwriter uses Python as its language rather than a custom DSL. By chosing an established language, we get:

* Full-featured editor support
    * syntax-highlighting, debugging, linting and code-analysis
* An established ecosystem
    * interfacing with external data (JSON/XML/Yaml) is easy
    * deriving data from external systems (*SQL, Cassandra, Elastic Search, ...) is easy
* A well-rounded language
    * No shortcomings unlike specialised DSL's, see looping and Terraform or evaluating expressions in Ansible

Finally, languages like Python, Javascript, Ruby and more feature strong text manipulation features such as multi-line strings, string interpolation and more.

### Ensure code-generation code looks like a normal project

To enable full editor support, Ghostwriter avoids implementing custom resolution of functions etc beyond resolving a snippet to a Python function. From that point onwards, everything is imported using the standard import mechanism and a suitable `sys.path`. This should enable editors to navigate the codebase.

### Limit impact of code-generator on design
Code generators can often impact the overall program design in unfortunate ways.

Ghostwriter allows you to embed generated code inside of regular files. This enabled fine-grained use for code-generation. For example, we void splitting code across files because some code is best generated while some is best written by hand.
By embedding the generated code this way, we also avoid pulling the entire code-base into the code generator.

Another conscious choice is to move the code-generator code out of the target files and into separate Python files. This accomplishes two things: it reduces the amount of noise in the target files and it moves the code-generator code out into a standard Python project which enjoys full IDE support, with syntax-highlighting, code-analysis, unit-testing support and so on.

In summary: we allow interlacing generated and hand-written code, but we maintian a separation of project code from the code-generator code.

### Be extensible

The snippet-abstraction is very basic. The snippet function simply gets a file handle and can write characters directly to the file. This extensibility enables the writing of other DSL's or mechanisms for generating code while reusing the basic framework. In fact, the [writer interface](writer.md) and [template DSL](template_dsl.md) which are included are built on top of the snippet abstraction.

## Pro's and cons

### Ghostwriter sucks if

* You are using Racket, Scheme or Lisp
    * Seriously, you are already using the perfect language for code-generation!
* You would like to do AST-based code generation
    * Scheme, Lisp, Rust and Julia support macros on the language level. Espcially Scheme and Lisp are nice in this regard.
* You want to dynamically generate new files based on some input model
    * You can do this, but it is not really supported or catered to, specifically, you would have to remove old files yourself.

### Ghostwriter rocks if

* You are OK with text/template-based code generation
* You wish to generate code/text across multiple languages
* Your language is very verbose or difficult to produce reusable code with
    * (Looking at you, Java)

