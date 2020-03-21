# Design choices

This document should give you a better idea of the principles behind the design of Ghostwriter. Hopefully this gives you a better sense of the tradeoffs involved and why each choice was made.

## Democratize code generation
A goal of Ghostwriter is to make code generation straightforward while retaining general applicability. Most code generators are developed for a specific, narrow purpose (e.g generate protobuf code) and often require knowledge of how compilers function to understand.

By contrast, Ghostwriter uses the popular React model to provide a template-based code generator which can quickly support a variety of use cases and for which the only expertise required is in writing templates representing the intended output.


## Composition
Ghostwriter is strongly inspired by React in that it also uses the idea of composable *Components* as its central building block for code generation.

The React community has simultaneously proven the Component model highly flexible, and spent years pondering how to best leverage it - discovering patterns and antipatterns in the process. By closely following this approach, many of their insights and patterns are readily translated into Ghostwriter.
Thus building components by composing existing components, container/presentational component separation and higher-order components (HOC's) are just some of the patterns that can be readily applied.


## DSL optimised for emitting formatted code
Many template languages are optimised to output HTML - in this usecase, making it hard to write readable templates without inserting a few additional newlines or some indentation which is included in the final HTML document is reasonable. After all, it is the structure of the HTML and the accompanying CSS which defines the layout shown - not the exact whitespace used inside the HTML.

However, emitting code is different. At best, additional indentation is permissible if non-standard and hard to read. At worst, as in the case of Python, wrong indentation is considered an error.

Ghostwriter's template DSL is designed solely to enable writing templates with properly indented content easily. To do this, the DSL separates the template from control-logic. This means that lines like if/for statements begin and end on lines which are stripped entirely from the final output.
This makes it much easier to see the structure of the final template and much less awkward to write these templates than in template languages where such blocks must wrap the actual content on the same lines as the content to avoid additional whitespace in the output.

The DSL is intentionally bare-bones - complex logic can be implemented as Python methods in the same component. This encourages separation of logic and template and means the code is available for the IDE to analyze and work on.


## Use a general-purpose language (Python)
Ghostwriter is meant to be a pragmatic code generator and this is why it uses Python rather than a custom DSL.

DSL's are very hard to get right, I learned this from fighting extensively with [Terraform](https://terraform.io) and especially [Ansible](https://ansible.com), both wonderful products with unfortunate DSL's.

Using a standard language in a project structure matching the expectations of the language also means that existing code editors and IDE's just work. Refactoring, type analysis, linting, unit testing libraries and so on can be used immediately.

Similarly, the Python ecosystem with all its libraries is available, making it possible to operate on JSON, YAML, HCL config files or interact with databases as diverse as Elastic Search, Postgres or MongoDB.
It also means that it is possible to write components and package them as libraries to easily reuse them across projects.

Finally, if you are already familiar with Python, the barrier to entry is lower. If not, it is a transferable skill well worth having whereas DSL's are typically tied to a given product.


## Separate code-generation logic from regular content
There are two benefits to moving code-generation code out into separate Python files. Firstly, it reduces the amount of noise in the target files. Secondly, following a standard Python project structure is what ensures full support from IDE's, code analysis- and unit-testing tools and more. It is also how it becomes easy to factor out common functionality into utility code and so on.

## Mix hand-written and generated code in files
By allowing a mixture of hand-written and generated code in the same file, Ghostwriter encourages granular use of code-generation. This ideally prevents pulling in more and more code into templates

## Be extensible
The snippet-abstraction is very basic. The snippet function simply gets a file handle and can write characters directly to the file. This extensibility enables the writing of other DSL's or mechanisms for generating code while reusing the basic framework. In fact, the [template DSL](template_dsl.md) is built on top of the snippet abstraction.

