# Introduction
> Ghostwriter: Someone who writes a book or article, etc. for another person to publish under his or her own name.

— Cambridge Dictionary


Ghostwriter is essentially what happens when trying to see how well the Component-abstraction from [React](https://reactjs.org/) can be applied to template-based code generation.

Code generation in Ghostwriter is *component-based*. Components in Ghostwriter are small, encapsulated building-blocks, containing a small `template` string, which uses a minimal DSL for generating the final output: 

```python
# A component for generating a Golang struct
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

The DSL is deliberately minimal - the idea is to separate template logic out into actual Python methods rather than inventing a complex template DSL. This also means that components can be written with full IDE support and use the full Python package ecosystem.

## Inject generated code into regular files
With ghostwriter, you define so-called **snippets** inside your code files to designate where the generated code goes. Everything between the start- and end line of a snippet is rewritten with the output of running the snippet each time the file is processed.


```golang
   package main
   import (
       "fmt
   )

   // <@@golang.struct@@>
   type person struct {
       name string
       age int
   }
   // <@@/golang.struct@@>

   func main() {
       fmt.Println(person{name: "Alice", age: 30})
   }
```

## Ghostwriter summarized

* A react-inspired template-based code generation system
* Reuse components to build ever larger components and to reuse components across projects
* Fully leverage the Python ecosystem
    * Use any library to interface with databases or help process data ahead of code generation.
    * IDE support: auto-completion, linting, type annotations and more - lean on industrial strength IDE's
    * Package components into a Python library to share across projects, internally or otherwise
* Fast feedback loop:
    * Written to be run in watch mode where files are processed and snippets re-run on change.